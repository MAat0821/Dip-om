import os
import json
import random
from flask import Flask, render_template
from pydub import AudioSegment
from .config import Config
from .models import db
from .api import api_bp


def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(__name__,
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))

    app.config.from_object(Config)
    db.init_app(app)
    app.register_blueprint(api_bp, url_prefix='/api')

    # ==================== ЗАГРУЗКА БАЗЫ ПЕСЕН ====================
    songs_db = []
    songs_file = os.path.join(base_dir, 'data', 'songs.json')
    try:
        with open(songs_file, 'r', encoding='utf-8') as f:
            songs_db = json.load(f)
        print(f"✅ Загружено {len(songs_db)} песенных сегментов")
    except Exception as e:
        print(f"❌ Ошибка загрузки songs.json: {e}")
        songs_db = []

    # ==================== ОСНОВНЫЕ МАРШРУТЫ ====================
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/host')
    def host():
        return render_template('host.html')

    @app.route('/player')
    def player():
        return render_template('player.html')

    # ==================== МАРШРУТ ТЕСТА ПО МУЗЫКЕ ====================
    @app.route('/music-quiz/<int:song_id>')
    def music_quiz_page(song_id):
        if song_id < 1 or song_id > len(songs_db):
            return render_template('error.html', message="Песня не найдена"), 404

        song = songs_db[song_id - 1]
        audio_dir = os.path.join(base_dir, 'audio')
        file_path = os.path.join(audio_dir, song.get('file', ''))

        # 1️⃣ Определяем реальную длительность файла
        real_duration_ms = 0
        try:
            audio = AudioSegment.from_mp3(file_path)
            real_duration_ms = len(audio)
        except Exception as e:
            print(f"⚠️ Не удалось определить длину файла {song.get('file')}: {e}")

        # 2️⃣ Рассчитываем длительность текущего сегмента
        segment_duration = song.get('end_time_ms', 0) - song.get('start_time_ms', 0)
        duration_str = f"{segment_duration // 60}:{segment_duration % 60:02d}"

        # 3️⃣ Генерируем вопросы из текста песни
        full_lyrics = song.get('full_lyrics', '').strip()
        words = full_lyrics.split()
        pauses = []

        if len(words) >= 3:
            # Рассчитываем позиции слов в рамках текущего сегмента
            for i in random.sample(range(len(words)), min(3, len(words))):
                # Время в мс от начала сегмента
                word_time_ms = song.get('start_time_ms', 0) + int((i / len(words)) * segment_duration)
                pauses.append({
                    'time': word_time_ms,
                    'prompt': f'Какое слово пропущено? (позиция {i + 1})',
                    'answer': words[i],
                    'correctFeedback': 'Верно! 🎉',
                    'incorrectFeedback': 'Попробуйте еще раз.'
                })

        # 4️⃣ Отдаём шаблон с данными
        return render_template('music_quiz.html',
                               song_title=song.get('title', 'Без названия'),
                               audio_file=song.get('file', ''),
                               total_duration=duration_str,
                               pauses=pauses,
                               real_duration=real_duration_ms)

    # ==================== ИНИЦИАЛИЗАЦИЯ БД ====================
    with app.app_context():
        db.create_all()

    return app