import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Путь к нашему .txt файлу
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "info.txt")

# Общие настройки для LLM (параметры ChatGPT)
LLM_MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 1.0