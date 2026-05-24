import sqlite3
import os

DB_NAME = "game.db"


def init_db():
    # Если файл уже есть, удаляем его, чтобы создать чистую БД
    if os.path.exists(DB_NAME):
        print(f"⚠️ {DB_NAME} уже существует. Создаю заново...")
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # SQL-скрипт для создания всех таблиц
    cursor.executescript('''
                         CREATE TABLE rooms
                         (
                             id         INTEGER PRIMARY KEY AUTOINCREMENT,
                             code       TEXT NOT NULL UNIQUE,
                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                         );

                         CREATE TABLE players
                         (
                             id        INTEGER PRIMARY KEY AUTOINCREMENT,
                             room_code TEXT NOT NULL,
                             nickname  TEXT NOT NULL,
                             FOREIGN KEY (room_code) REFERENCES rooms (code)
                         );

                         CREATE TABLE answers
                         (
                             id          INTEGER PRIMARY KEY AUTOINCREMENT,
                             player_id   INTEGER NOT NULL,
                             room_code   TEXT    NOT NULL,
                             chosen_word TEXT    NOT NULL,
                             status      TEXT DEFAULT 'pending',
                             FOREIGN KEY (player_id) REFERENCES players (id)
                         );
                         ''')

    conn.commit()
    conn.close()
    print(f"✅ База данных {DB_NAME} успешно создана!")


if __name__ == '__main__':
    init_db()