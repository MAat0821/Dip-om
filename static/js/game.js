// game.js - Основной JavaScript для квиз-игры

document.addEventListener('DOMContentLoaded', function() {
    const roomCodeInput = document.getElementById('roomCode');
    const nicknameInput = document.getElementById('nickname');

    // Авто-перевод в верхний регистр и автофокус
    if (roomCodeInput) {
        roomCodeInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.toUpperCase();
            if (e.target.value.length === 6 && nicknameInput) {
                nicknameInput.focus();
            }
        });
    }
});

// Подключение к игре
async function joinGame() {
    const roomCode = document.getElementById('roomCode').value.toUpperCase().trim();
    const nickname = document.getElementById('nickname').value.trim();
    const errorEl = document.getElementById('joinError');

    if (!roomCode || roomCode.length < 4) {
        if (errorEl) {
            errorEl.textContent = '⚠️ Введите корректный код комнаты';
            errorEl.style.color = '#dc3545';
        }
        return;
    }

    if (!nickname) {
        if (errorEl) {
            errorEl.textContent = '⚠️ Введите никнейм';
            errorEl.style.color = '#dc3545';
        }
        return;
    }

    try {
        const response = await fetch('/api/join', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({room_code: roomCode, nickname: nickname})
        });

        const data = await response.json();

        if (data.success) {
            window.location.href = `/player/${roomCode}/${data.player_id}`;
        } else {
            if (errorEl) {
                errorEl.textContent = '❌ ' + (data.error || 'Ошибка подключения');
                errorEl.style.color = '#dc3545';
            }
        }
    } catch (error) {
        if (errorEl) {
            errorEl.textContent = '❌ Ошибка сети';
            errorEl.style.color = '#dc3545';
        }
    }
}