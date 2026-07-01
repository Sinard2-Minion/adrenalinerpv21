import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env (если он есть локально)
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", 0))
REVIEWS_CHANNEL_ID = int(os.getenv("REVIEWS_CHANNEL_ID", 0))
WICK_LOGS_CHANNEL_ID = int(os.getenv("WICK_LOGS_CHANNEL_ID", 0))
AUDIO_LOGS_CHANNEL_ID = int(os.getenv("AUDIO_LOGS_CHANNEL_ID", 0))
