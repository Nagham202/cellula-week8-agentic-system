import config
from groq import Groq


def transcribe_audio(audio_bytes):
    client = Groq(api_key=config.GROQ_API_KEY)

    transcription = client.audio.transcriptions.create(
        file=("recording.wav", audio_bytes),
        model="whisper-large-v3",
        response_format="json"
    )

    return transcription.text.strip()
