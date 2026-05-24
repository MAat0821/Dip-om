import  io
from pydub import AudioSegment, silence
from .config import Config

def generate_audio_stream(song_name, start_ms, end_ms):


    file_path = f"{Config.AUDIO_DIR}/{song_name}.mp3"

    try:
        audio = AudioSegment.from_mp3(file_path)

        #Создаем тыишину вместо вырезанного участка
        silence = AudioSegment.silent(duration=(end_ms - start_ms))

        final_audio = audio[:start_ms] + silence + audio[end_ms:]

        buffer = io.BytesIO()
        final_audio.export(buffer, format="mp3")
        buffer.seek(0)

        return buffer
    except Exception as e:
        print(f"Audio Error: {e}")
        return None
