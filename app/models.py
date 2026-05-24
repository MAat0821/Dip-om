from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(4), unique=True, nullable=False)
    current_song_index = db.Column(db.Integer, default=0)  # 🔥 Индекс закрепленной песни для комнаты
    players = db.relationship('Player', backref='room', lazy=True)
    answers = db.relationship('Answer', backref='room', lazy=True)


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(50), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    chosen_word = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')