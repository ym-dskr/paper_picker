import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI設定
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # メール設定
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
    RECIPIENT_EMAILS = os.getenv('RECIPIENT_EMAILS', '').split(',')
    
    # 検索設定
    MAX_PAPERS = int(os.getenv('MAX_PAPERS', 10))
    SEARCH_KEYWORDS = os.getenv('SEARCH_KEYWORDS', '').split(',')
    DAYS_BACK = int(os.getenv('DAYS_BACK', 7))
    
    # データベース
    DB_PATH = 'data/papers.db'
    
    # ログ設定
    LOG_PATH = 'logs/system.log'