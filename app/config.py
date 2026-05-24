import os

class Config:
    SECRET_KEY = 'dev-key-change-in-prod'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///quiz.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    Audio_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'audio')