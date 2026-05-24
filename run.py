from app import create_app

# Создаём экземпляр приложения
app = create_app()

# Запускаем сервер в режиме отладки
if __name__ == '__main__':
    print("=" * 50)
    print("🎮 Квиз-игра 'Студенческая весна'")
    print("=" * 50)
    print("📁 База данных: game.db")
    print(" Аудиофайлы: папка audio/")
    print("=" * 50)
    print("🚀 Сервер запущен!")
    print("🌐 Откройте в браузере: http://127.0.0.1:5000")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)