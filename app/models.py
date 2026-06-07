from app import db
from datetime import datetime
import random
import string


def generate_room_code():
    """Генерирует код комнаты (6 символов)"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class GameRoom(db.Model):
    """Комната игры"""
    __tablename__ = 'game_room'

    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(6), unique=True, nullable=False, index=True)
    host_name = db.Column(db.String(100), nullable=False)
    game_type = db.Column(db.String(50), default='quiz')  # 'music_test', 'guess_melody', 'quiz'
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    current_question = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    players = db.relationship('Player', backref='room', lazy=True, cascade='all, delete-orphan')
    answers = db.relationship('PlayerAnswer', backref='room', lazy=True, cascade='all, delete-orphan')


class Player(db.Model):
    """Игрок"""
    __tablename__ = 'player'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('game_room.id'), nullable=False)
    nickname = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    is_connected = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    answers = db.relationship('PlayerAnswer', backref='player', lazy=True, cascade='all, delete-orphan')


class Question(db.Model):
    """Вопросы для викторины"""
    __tablename__ = 'question'

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.String(200), nullable=False)
    variant_1 = db.Column(db.String(200), default='')
    variant_2 = db.Column(db.String(200), default='')
    variant_3 = db.Column(db.String(200), default='')
    question_type = db.Column(db.String(50), default='text')  # 'text', 'music', 'image'
    round_number = db.Column(db.Integer, default=1)
    points = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MusicTrack(db.Model):
    """Музыкальные треки"""
    __tablename__ = 'music_track'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), default='')
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500))
    duration = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class PlayerAnswer(db.Model):
    """Ответы игроков"""
    __tablename__ = 'player_answer'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('game_room.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    question_id = db.Column(db.Integer, nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Уникальность: один игрок может ответить на один вопрос только один раз
    __table_args__ = (
        db.UniqueConstraint('player_id', 'question_id', name='unique_player_question_answer'),
    )