import os
import json
import random
import io
import string
from flask import Blueprint, request, jsonify, send_file

# ==================== 1. НАСТРОЙКА FFMPEG ====================
FFMPEG_BIN = r"C:\Users\Maat7\OneDrive\Desktop\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
FFPROBE_BIN = r"C:\Users\Maat7\OneDrive\Desktop\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe"

if os.path.exists(FFMPEG_BIN) and os.path.exists(FFPROBE_BIN):
    os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_BIN)
    print(f"✅ FFmpeg найден: {os.path.dirname(FFMPEG_BIN)}")
else:
    print(f"❌ FFmpeg не найден. Проверьте путь.")
    FFMPEG_BIN = "ffmpeg"
    FFPROBE_BIN = "ffprobe"

from pydub import AudioSegment

AudioSegment.converter = FFMPEG_BIN
AudioSegment.ffprobe = FFPROBE_BIN

from .models import db, Room, Player, Answer

# ==================== 2. БАЗОВЫЕ НАСТРОЙКИ ====================
api_bp = Blueprint('api', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SONGS_FILE = os.path.join(BASE_DIR, 'data', 'songs.json')
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')

try:
    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        SONGS_DB = json.load(f)
    print(f"✅ Загружено {len(SONGS_DB)} песен")
except Exception as e:
    print(f"⚠️ Ошибка загрузки songs.json: {e}")
    SONGS_DB = []


# ==================== 3. ФУНКЦИИ ОБРАБОТКИ АУДИО ====================
def get_audio_duration(file_path):
    """Получает длину аудиофайла в миллисекундах"""
    try:
        audio = AudioSegment.from_mp3(file_path)
        return len(audio)
    except Exception as e:
        print(f"❌ Ошибка определения длины файла {file_path}: {e}")
        return 0


def generate_audio_buffer(song_filename: str, clip_start_ms: int, clip_end_ms: int, silence_point_ms: int):
    file_path = os.path.join(AUDIO_DIR, song_filename)
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return None

    try:
        # Получаем реальную длину файла
        real_duration = get_audio_duration(file_path)
        if real_duration == 0:
            print(f"❌ Невозможно определить длину файла: {file_path}")
            return None

        # Корректируем границы клипа, если файл короче заявленного
        clip_start_ms = max(0, min(clip_start_ms, real_duration))
        clip_end_ms = max(clip_start_ms + 1000, min(clip_end_ms, real_duration))
        clip_duration_ms = clip_end_ms - clip_start_ms

        # Загружаем аудио
        audio = AudioSegment.from_mp3(file_path)
        clip = audio[clip_start_ms:clip_end_ms]

        # Защита от краёв тишины
        silence_point_ms = max(500, min(silence_point_ms, clip_duration_ms - 2000))
        silence_dur = 1500  # Длительность тишины в мс

        # Создаём тишину и склеиваем
        silence = AudioSegment.silent(duration=silence_dur)
        final_audio = clip[:silence_point_ms].fade_out(100) + silence + clip[silence_point_ms:].fade_in(100)

        # Сохраняем в буфер
        buffer = io.BytesIO()
        final_audio.export(buffer, format="mp3")
        buffer.seek(0)
        print(
            f"✅ Готово: [{clip_start_ms}-{clip_end_ms}мс] | Тишина на {silence_point_ms}мс (реальная длина: {real_duration}мс)")
        return buffer
    except Exception as e:
        print(f"🔊 Ошибка аудио: {e}")
        return None


# ==================== 4. МАРШРУТЫ ====================
@api_bp.route('/create-room', methods=['POST'])
def create_room():
    code = ''.join(random.choices(string.ascii_uppercase + "23456789", k=4))
    try:
        new_room = Room(code=code)
        db.session.add(new_room)
        db.session.commit()
        return jsonify({"success": True, "code": code, "room_id": new_room.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/join-room', methods=['POST'])
def join_room():
    data = request.get_json()
    code = data.get('code', '').strip().upper()
    nickname = data.get('nickname', '').strip()
    if not code or not nickname:
        return jsonify({"success": False, "error": "Укажите код и никнейм"}), 400

    room = Room.query.filter_by(code=code).first()
    if not room:
        return jsonify({"success": False, "error": "Комната не найдена"}), 404

    try:
        player = Player(nickname=nickname, room_id=room.id)
        db.session.add(player)
        db.session.commit()
        return jsonify({"success": True, "player_id": player.id, "room_id": room.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/get-quiz', methods=['GET'])
def get_quiz():
    if not SONGS_DB:
        return jsonify({"error": "База пуста"}), 500

    # Выбираем случайную песню
    song = random.choice(SONGS_DB)
    full_lyrics = song.get('full_lyrics', '').strip()

    if not full_lyrics or len(full_lyrics) < 10:
        return jsonify({"error": "Нет данных для теста"}), 500

    words = full_lyrics.split()
    if len(words) < 3:
        return jsonify({"error": "Недостаточно слов для теста"}), 500

    # Получаем реальную длину файла
    file_path = os.path.join(AUDIO_DIR, song.get('file', ''))
    real_duration_ms = get_audio_duration(file_path)

    # Границы клипа
    clip_start_ms = song.get('start_time_ms', 0)
    clip_end_ms = song.get('end_time_ms', 60000)

    # Коррекция, если файл короче
    if real_duration_ms < clip_end_ms:
        clip_end_ms = real_duration_ms

    clip_duration_ms = clip_end_ms - clip_start_ms
    if clip_duration_ms <= 0:
        return jsonify({"error": "Некорректные временные метки"}), 500

    # 🎯 ГЛАВНОЕ ИСПРАВЛЕНИЕ: ПРОВЕРКА НА РУЧНУЮ СИНХРОНИЗАЦИЮ
    # Мы ищем в JSON поля 'target_word' и 'silence_time_ms'
    target_word_manual = song.get('target_word')
    time_manual = song.get('silence_time_ms')

    target_idx = 0
    target_word = ""

    # Если в JSON есть точные данные — используем их
    if target_word_manual and time_manual is not None and target_word_manual in words:
        target_word = target_word_manual
        target_idx = words.index(target_word)
        # Переводим абсолютное время в время относительно начала клипа
        silence_point_ms = time_manual - clip_start_ms
        print(f"🎯 ТОЧНАЯ СИНХРОНИЗАЦИЯ: Слово '{target_word}' на {silence_point_ms}мс")
    else:
        # Если точных данных нет — берем случайное слово (старый метод)
        target_idx = random.randint(0, len(words) - 1)
        target_word = words[target_idx]

        # Старая формула (неточная, но работает если нет таймингов)
        word_ratio = target_idx / len(words)
        silence_point_ms = int(word_ratio * clip_duration_ms)
        print(f"⚠️ АВТО-РАСЧЕТ: Слово '{target_word}' на ~{silence_point_ms}мс")

    # Скрываем слово
    words[target_idx] = "_" * len(target_word)
    masked_lyrics = " ".join(words)

    # Защита от краёв
    silence_point_ms = max(2000, min(silence_point_ms, clip_duration_ms - 3000))

    return jsonify({
        "title": song.get('title', 'Без названия'),
        "full_lyrics": full_lyrics,
        "lyrics": masked_lyrics,
        "answer": target_word,
        "song_file": song.get('file', ''),
        "clip_start_ms": clip_start_ms,
        "clip_end_ms": clip_end_ms,
        "silence_point_ms": silence_point_ms,
        "real_duration_ms": real_duration_ms
    })


@api_bp.route('/stream-audio', methods=['GET'])
def stream_audio():
    song_file = request.args.get('song')
    clip_start_ms = request.args.get('clip_start_ms', type=int, default=0)
    clip_end_ms = request.args.get('clip_end_ms', type=int, default=60000)
    silence_point_ms = request.args.get('silence_point_ms', type=int, default=15000)

    if not song_file:
        return jsonify({"error": "Не указан файл"}), 400

    buffer = generate_audio_buffer(song_file, clip_start_ms, clip_end_ms, silence_point_ms)
    if not buffer:
        return jsonify({"error": "Ошибка обработки аудио"}), 404

    return send_file(buffer, mimetype="audio/mpeg")


@api_bp.route('/submit-answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    room_code = data.get('room_code')
    nickname = data.get('nickname')
    guess = data.get('guess', '').strip()

    if not room_code or not nickname or not guess:
        return jsonify({"success": False, "error": "Неполные данные"}), 400

    try:
        # 1. Находим комнату по коду
        room = Room.query.filter_by(code=room_code).first()
        if not room:
            return jsonify({"success": False, "error": "Комната не найдена"}), 404

        # 2. Находим игрока
        player = Player.query.filter_by(nickname=nickname, room_id=room.id).first()
        if not player:
            player = Player(nickname=nickname, room_id=room.id)
            db.session.add(player)
            db.session.flush()

        # 3. Сохраняем ответ
        answer = Answer(
            player_id=player.id,
            room_id=room.id,
            chosen_word=guess,
            status='pending'
        )
        db.session.add(answer)
        db.session.commit()
        print(f"✅ Ответ принят: {nickname} -> {guess}")  # Лог для проверки

        return jsonify({"success": True, "message": "Ответ отправлен"})

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка БД при отправке ответа: {e}")
        return jsonify({"success": False, "error": "Ошибка сервера"}), 500


@api_bp.route('/get-answers/<int:room_id>', methods=['GET'])
def get_answers(room_id):
    try:
        # ИЗМЕНЕНИЕ: Показываем ВСЕ ответы, а не только pending, чтобы вы видели их в консоли
        answers = Answer.query.filter_by(room_id=room_id).order_by(Answer.id.desc()).limit(20).all()

        result = []
        for a in answers:
            result.append({
                "id": a.id,
                "nickname": a.player.nickname if a.player else "Аноним",
                "word": a.chosen_word,
                "status": a.status
            })
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка get_answers: {e}")
        return jsonify([])


@api_bp.route('/approve-answer/<int:answer_id>', methods=['POST'])
def approve_answer(answer_id):
    ans = Answer.query.get(answer_id)
    if ans:
        ans.status = 'approved'
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Не найден"}), 404