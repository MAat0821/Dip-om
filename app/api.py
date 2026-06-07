from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from app.models import db, GameRoom, Player, Question, MusicTrack, generate_room_code
import os
import random

# Создаём blueprint'ы
api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ===== ГЛАВНАЯ СТРАНИЦА =====
@api_bp.route('/')
def index():
    """Главная страница - рендерит HTML"""
    return render_template('index.html')


# ===== ВЕДУЩИЙ (HOST) =====
@api_bp.route('/host')
def host_redirect():
    """Перенаправление на создание комнаты"""
    return redirect(url_for('api.host_create'))


@api_bp.route('/host/create', methods=['GET', 'POST'])
def host_create():
    """Создание новой комнаты"""
    if request.method == 'POST':
        host_name = request.form.get('host_name', 'Ведущий')
        game_type = request.form.get('game_type', 'quiz')

        # Генерируем уникальный код
        room_code = generate_room_code()
        while GameRoom.query.filter_by(room_code=room_code).first():
            room_code = generate_room_code()

        room = GameRoom(
            room_code=room_code,
            host_name=host_name,
            game_type=game_type,
            status='waiting'
        )

        db.session.add(room)
        db.session.commit()

        return redirect(url_for('api.host_panel', room_code=room_code))

    return render_template('host_create.html')


@api_bp.route('/host/<room_code>')
def host_panel(room_code):
    """Панель ведущего"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    players = Player.query.filter_by(room_id=room.id, is_connected=True).all()
    return render_template('host_panel.html', room=room, players=players)


@api_bp.route('/host/music')
@api_bp.route('/host/music/<room_code>')
def host_music(room_code=None):
    """Страница управления музыкой для ведущего"""
    return render_template('host_music.html', room_code=room_code)


# ===== ИГРОКИ (PLAYERS) =====
@api_bp.route('/join', methods=['GET', 'POST'])
def join_room():
    """Страница подключения"""
    if request.method == 'GET':
        return render_template('join.html')

    # POST обрабатывается через API
    return redirect(url_for('api.index'))


# ===== API МАРШРУТЫ =====

@api_bp.route('/api/status')
def api_status():
    """Проверка статуса API"""
    return jsonify({'message': 'API работает'})


@api_bp.route('/api/join', methods=['POST'])
def api_join():
    """Подключение игрока к комнате"""
    data = request.json
    room_code = data.get('room_code', '').upper()
    nickname = data.get('nickname', '').strip()

    if not room_code or len(room_code) < 4:
        return jsonify({'success': False, 'error': 'Неверный код комнаты'})

    if not nickname:
        return jsonify({'success': False, 'error': 'Введите никнейм'})

    room = GameRoom.query.filter_by(room_code=room_code).first()
    if not room:
        return jsonify({'success': False, 'error': 'Комната не найдена'})

    if room.status != 'waiting':
        return jsonify({'success': False, 'error': 'Игра уже началась'})

    # Проверяем, не присоединился ли уже
    player = Player.query.filter_by(room_id=room.id, nickname=nickname).first()
    if not player:
        player = Player(room_id=room.id, nickname=nickname)
        db.session.add(player)
        db.session.commit()

    return jsonify({
        'success': True,
        'player_id': player.id,
        'room_code': room_code
    })


@api_bp.route('/api/room/<room_code>/status')
def get_room_status(room_code):
    """Получить статус комнаты"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    players_count = Player.query.filter_by(room_id=room.id, is_connected=True).count()

    return jsonify({
        'status': room.status,
        'current_question': room.current_question,
        'players_count': players_count,
        'game_type': room.game_type
    })


@api_bp.route('/api/room/<room_code>/start', methods=['POST'])
def start_game(room_code):
    """Начать игру"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    room.status = 'playing'
    room.current_question = 1
    db.session.commit()
    return jsonify({'success': True, 'status': 'playing'})


@api_bp.route('/api/room/<room_code>/next-question', methods=['POST'])
def next_question(room_code):
    """Следующий вопрос"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    room.current_question += 1
    db.session.commit()
    return jsonify({'success': True, 'question_number': room.current_question})


@api_bp.route('/api/room/<room_code>/leaderboard')
def get_leaderboard(room_code):
    """Получить таблицу лидеров"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    players = Player.query.filter_by(room_id=room.id, is_connected=True) \
        .order_by(Player.score.desc()).all()

    return jsonify([{
        'nickname': p.nickname,
        'score': p.score
    } for p in players])


@api_bp.route('/api/room/<room_code>/players')
def get_players(room_code):
    """Получить список игроков"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    players = Player.query.filter_by(room_id=room.id, is_connected=True).all()

    return jsonify([{
        'id': p.id,
        'nickname': p.nickname,
        'score': p.score
    } for p in players])


@api_bp.route('/api/player/<int:player_id>/answer', methods=['POST'])
def submit_answer(player_id):
    """Отправить ответ"""
    data = request.json
    player = Player.query.get_or_404(player_id)

    is_correct = data.get('is_correct', False)

    # Обновляем счёт если ответ правильный
    if is_correct:
        player.score += 10

    db.session.commit()
    return jsonify({'success': True, 'score': player.score})


# ===== НОВЫЙ МАРШРУТ: Список вопросов =====
@api_bp.route('/api/questions/list')
def get_questions_list():
    """Получить список всех вопросов"""
    questions = Question.query.order_by(Question.round_number).all()
    return jsonify([{
        'id': q.id,
        'text': q.text,
        'correct_answer': q.correct_answer,
        'variant_1': q.variant_1,
        'variant_2': q.variant_2,
        'variant_3': q.variant_3,
        'question_type': q.question_type,
        'round_number': q.round_number,
        'points': q.points
    } for q in questions])


# ===== СТРАНИЦЫ ИГРОКА =====
@api_bp.route('/player/<room_code>/<int:player_id>')
def player_lobby(room_code, player_id):
    """Лобби игрока"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    player = Player.query.get_or_404(player_id)
    return render_template('player_lobby.html', room=room, player=player)


@api_bp.route('/player/<room_code>/<int:player_id>/game')
def player_game(room_code, player_id):
    """Игровой экран игрока"""
    room = GameRoom.query.filter_by(room_code=room_code).first_or_404()
    player = Player.query.get_or_404(player_id)
    return render_template('player_game.html', room=room, player=player)


# ===== РАЗДАЧА АУДИО =====
@api_bp.route('/audio/<filename>')
def serve_audio(filename):
    """Раздача аудиофайлов из папки audio/"""
    audio_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audio')
    print(f"🎵 Ищем аудио в: {audio_folder}/{filename}")
    return send_from_directory(audio_folder, filename)


@api_bp.route('/api/music/list')
def get_music_list():
    """Получить список всех загруженных треков"""
    tracks = MusicTrack.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'artist': t.artist,
        'filename': t.filename,
        'url': f'/audio/{t.filename}'
    } for t in tracks])


# ===== АДМИНКА =====
@admin_bp.route('/')
def admin_dashboard():
    """Главная страница админки"""
    questions_count = Question.query.count()
    tracks_count = MusicTrack.query.count()
    return render_template('admin/dashboard.html',
                           questions_count=questions_count,
                           tracks_count=tracks_count)


@admin_bp.route('/questions')
@admin_bp.route('/questions/<room_code>')
def admin_questions(room_code=None):
    """Список вопросов"""
    questions = Question.query.order_by(Question.round_number).all()
    return render_template('admin/questions.html', questions=questions, room_code=room_code)


@admin_bp.route('/questions/add', methods=['POST'])
def add_question():
    """Добавить вопрос"""
    data = request.json
    question = Question(
        text=data['text'],
        correct_answer=data['correct_answer'],
        variant_1=data.get('variant_1', ''),
        variant_2=data.get('variant_2', ''),
        variant_3=data.get('variant_3', ''),
        question_type=data.get('question_type', 'text'),
        round_number=data.get('round_number', 1),
        points=data.get('points', 1)
    )
    db.session.add(question)
    db.session.commit()
    return jsonify({'success': True, 'id': question.id})


@admin_bp.route('/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """Удалить вопрос"""
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/music')
@admin_bp.route('/music/<room_code>')
def admin_music(room_code=None):
    """Список треков"""
    tracks = MusicTrack.query.order_by(MusicTrack.upload_date.desc()).all()
    return render_template('admin/music.html', tracks=tracks, room_code=room_code)


@admin_bp.route('/music/upload', methods=['POST'])
def upload_music():
    """Загрузить трек"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Нет файла'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Файл не выбран'}), 400

    filename = secure_filename(file.filename)

    # Сохраняем в папку audio/ (в корне проекта)
    audio_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'audio')
    os.makedirs(audio_folder, exist_ok=True)
    filepath = os.path.join(audio_folder, filename)
    file.save(filepath)

    track = MusicTrack(
        title=request.form.get('title', filename),
        artist=request.form.get('artist', ''),
        filename=filename,
        filepath=filepath
    )
    db.session.add(track)
    db.session.commit()

    return jsonify({'success': True, 'id': track.id})


@admin_bp.route('/music/<int:track_id>', methods=['DELETE'])
def delete_music(track_id):
    """Удалить трек"""
    track = MusicTrack.query.get_or_404(track_id)
    if os.path.exists(track.filepath):
        os.remove(track.filepath)
    db.session.delete(track)
    db.session.commit()
    return jsonify({'success': True})