// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
let currentRoomCode = "";
let currentAnswer = "";
let currentPlayerId = null;
let currentRoomId = null;
let audioPlayer = null;
let isPlaying = false;

// ==================== ЛОГИКА ГЛАВНОЙ СТРАНИЦЫ (index.html) ====================
function joinGame() {
    const code = document.getElementById('roomCode')?.value.trim().toUpperCase();
    const nickname = document.getElementById('nickname')?.value.trim();
    const errorText = document.getElementById('joinError');

    if (errorText) errorText.innerText = "";

    if (!code || !nickname) {
        if (errorText) errorText.innerText = "Заполните код и никнейм!";
        return;
    }

    fetch('/api/join-room', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code, nickname: nickname })
    })
    .then(async response => {
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            window.location.href = `/player?code=${code}&nickname=${encodeURIComponent(nickname)}`;
        } else {
            if (errorText) errorText.innerText = data.error || "Ошибка входа";
        }
    })
    .catch(error => {
        console.error('Ошибка подключения:', error);
        if (errorText) errorText.innerText = error.message || "Не удалось подключиться к серверу";
    });
}

// ==================== ЛОГИКА ХОСТА (host.html) ====================
function initHost() {
    fetch('/api/create-room', { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            currentRoomCode = data.code;
            currentRoomId = data.room_id;

            const codeEl = document.getElementById('displayCode');
            if (codeEl) codeEl.innerText = currentRoomCode;

            loadHostQuiz();
            setInterval(pollAnswers, 2000);
        }
    })
    .catch(error => console.error('Ошибка создания комнаты:', error));
}

function pollAnswers() {
    if (!currentRoomId) return;

    fetch(`/api/get-answers/${currentRoomId}`)
    .then(res => res.json())
    .then(data => {
        const list = document.getElementById('answersList');
        if (!list) return;

        list.innerHTML = "";
        if (!data || data.length === 0) {
            list.innerHTML = "<li class='text-muted'>Пока нет ответов...</li>";
        } else {
            data.forEach(item => {
                const li = document.createElement('li');
                li.className = 'answer-item';

                // Индикация статуса: ✅ одобрено, ⏳ ожидает
                const statusIcon = item.status === 'approved' ? '✅' : '⏳';
                const approveBtn = item.status === 'approved'
                    ? '<span style="color:#aaa">Проверено</span>'
                    : `<button class="approve-btn" onclick="approveAnswer(${item.id})">✅</button>`;

                li.innerHTML = `
                    <span>${statusIcon} <b>${item.nickname}</b>: "${item.word}"</span>
                    ${approveBtn}
                `;
                list.appendChild(li);
            });
        }
    })
    .catch(error => console.error('Ошибка опроса ответов:', error));
}

function approveAnswer(answerId) {
    fetch(`/api/approve-answer/${answerId}`, { method: 'POST' })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            pollAnswers();
        }
    })
    .catch(error => console.error('Ошибка одобрения:', error));
}

function loadHostQuiz() {
    fetch('/api/get-quiz')
    .then(res => res.json())
    .then(data => {
        const titleEl = document.getElementById('songTitle');
        const lyricsEl = document.getElementById('fullLyrics');

        if (titleEl) titleEl.innerText = data.title;
        if (lyricsEl) lyricsEl.innerText = data.full_lyrics;
    })
    .catch(error => console.error('Ошибка загрузки вопроса:', error));
}

// ==================== ЛОГИКА ИГРОКА (player.html) ====================
function initPlayer() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const nick = urlParams.get('nickname');

    if (!code || !nick) {
        const lyricsEl = document.getElementById('maskedLyrics');
        if (lyricsEl) lyricsEl.innerHTML = '❌ Ошибка: неверные параметры';
        return;
    }

    currentRoomCode = code;

    const nickEl = document.getElementById('playerNick');
    if (nickEl) nickEl.innerText = nick;

    audioPlayer = document.getElementById('audioPlayer');
    if (audioPlayer) {
        audioPlayer.addEventListener('ended', () => {
            console.log('🔚 Аудио закончилось');
            isPlaying = false;
        });
    }

    loadPlayerQuiz();
}

function loadPlayerQuiz() {
    console.log('🔄 Загрузка раунда...');

    fetch('/api/get-quiz')
    .then(res => {
        console.log('📡 Статус:', res.status);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res.json();
    })
    .then(data => {
        console.log('✅ Данные:', data);

        if (data.error) {
            document.getElementById('resultMsg').innerHTML = `❌ ${data.error}`;
            return;
        }

        currentAnswer = data.answer;

        // Текст с пропуском
        const lyricsEl = document.getElementById('maskedLyrics');
        if (lyricsEl && data.lyrics) {
            const formatted = data.lyrics.replace(/_+/g, '<span class="hidden-word">???</span>');
            lyricsEl.innerHTML = formatted;
        }

        // 🔥 Загрузка аудио
        const audioPlayer = document.getElementById('audioPlayer');
        if (audioPlayer && data.song_file) {
            const params = new URLSearchParams({
                song: data.song_file,
                clip_start_ms: data.clip_start_ms || 0,
                clip_end_ms: data.clip_end_ms || 60000,
                silence_point_ms: data.silence_point_ms || 15000
            });

            audioPlayer.src = `/api/stream-audio?${params.toString()}`;
            audioPlayer.load();
            audioPlayer.play().catch(e => console.error('❌ Ошибка воспроизведения:', e));
            isPlaying = true;

            console.log(`🎵 Клип: ${data.clip_start_ms}-${data.clip_end_ms}мс`);
            console.log(`🔇 Тишина на ${data.silence_point_ms}мс`);
        }
    })
    .catch(error => {
        console.error('❌ Ошибка загрузки:', error);
        const resultEl = document.getElementById('resultMsg');
        if (resultEl) {
            resultEl.innerHTML = `❌ Ошибка: ${error.message}`;
        }
    });
}

function submitGuess() {
    const guess = document.getElementById('guessInput')?.value.trim();
    if (!guess) return;

    const nick = document.getElementById('playerNick')?.innerText || 'Игрок';
    const resultEl = document.getElementById('resultMsg');

    // Визуальный статус отправки
    if (resultEl) resultEl.innerHTML = '<span style="color:#aaa">Отправка...</span>';

    console.log(`📤 Отправка: room_code="${currentRoomCode}", nick="${nick}", guess="${guess}"`);

    fetch('/api/submit-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            room_code: currentRoomCode,
            nickname: nick,
            guess: guess
        })
    })
    .then(res => res.json())
    .then(data => {
        console.log('📥 Ответ сервера:', data);
        if (resultEl) {
            if (data.success) {
                resultEl.innerHTML = '<span style="color:#4caf50; font-weight:bold">✅ Ответ отправлен!</span>';
                document.getElementById('guessInput').value = '';

                // Очищаем сообщение через 3 секунды
                setTimeout(() => {
                    if (resultEl) resultEl.innerHTML = '';
                }, 3000);
            } else {
                resultEl.innerHTML = `<span style="color:#e94560">❌ ${data.error || 'Ошибка'}</span>`;
            }
        }
    })
    .catch(error => {
        console.error('Ошибка отправки:', error);
        if (resultEl) resultEl.innerHTML = '<span style="color:#e94560">❌ Ошибка сети</span>';
    });
}

// ==================== АУДИО-КНОПКИ ====================
function toggleAudio() {
    if (!audioPlayer) return;

    const playBtn = document.getElementById('playBtn');
    if (isPlaying) {
        audioPlayer.pause();
        isPlaying = false;
        if (playBtn) playBtn.textContent = '▶️';
    } else {
        audioPlayer.play().catch(e => console.error('❌ Ошибка play:', e));
        isPlaying = true;
        if (playBtn) playBtn.textContent = '⏸';
    }
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================
document.addEventListener('DOMContentLoaded', function() {
    // Авто-определение страницы
    if (document.getElementById('displayCode')) {
        initHost();
    }
    else if (document.getElementById('playerNick')) {
        initPlayer();
    }

    // Обработка Enter в поле ответа
    const guessInput = document.getElementById('guessInput');
    if (guessInput) {
        guessInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') submitGuess();
        });
    }

    // Кнопка Play/Pause
    const playBtn = document.getElementById('playBtn');
    if (playBtn) {
        playBtn.addEventListener('click', toggleAudio);
    }
});