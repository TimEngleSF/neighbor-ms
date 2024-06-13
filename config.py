import os
from dotenv import load_dotenv

load_dotenv()
CLIENT_KEY = os.getenv("CLIENT_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")
WEBHOOK_KEY = os.getenv("WEBHOOK_KEY")
LEONARDO_KEY = os.getenv("LEONARDO_KEY")
