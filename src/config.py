"""論文ピッカーシステムの設定管理

このモジュールは、研究論文要約システムの全ての設定を管理します。
APIキー、メール設定、検索パラメータなどを含みます。
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()


class Config:
    """論文ピッカーシステムの設定クラス
    
    環境変数から読み込まれた設定を管理し、適切なデフォルト値と
    バリデーションを提供します。
    
    属性:
        OPENAI_API_KEY (str): LLMサービス用のOpenAI APIキー
        SMTP_SERVER (str): メール送信用のSMTPサーバーホスト名
        SMTP_PORT (int): SMTPサーバーのポート番号
        SENDER_EMAIL (str): 通知メール送信用のメールアドレス
        SENDER_PASSWORD (str): メール認証用のパスワード
        RECIPIENT_EMAILS (List[str]): 受信者メールアドレスのリスト
        MAX_PAPERS (int): 要約対象論文の最大数
        SEARCH_KEYWORDS (List[str]): 論文検索用のキーワードリスト
        DAYS_BACK (int): 検索対象期間（日数）
        DB_PATH (str): SQLiteデータベースファイルのパス
        LOG_PATH (str): ログファイルのパス
    """
    
    # OpenAI設定
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    # メール設定
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL: Optional[str] = os.getenv('SENDER_EMAIL')
    SENDER_PASSWORD: Optional[str] = os.getenv('SENDER_PASSWORD')
    RECIPIENT_EMAILS: List[str] = [
        email.strip() for email in os.getenv('RECIPIENT_EMAILS', '').split(',')
        if email.strip()
    ]
    
    # 検索設定
    MAX_PAPERS: int = int(os.getenv('MAX_PAPERS', '10'))
    SEARCH_KEYWORDS: List[str] = [
        keyword.strip() for keyword in os.getenv('SEARCH_KEYWORDS', '').split(',')
        if keyword.strip()
    ]
    DAYS_BACK: int = int(os.getenv('DAYS_BACK', '7'))
    
    # ファイルパス
    DB_PATH: str = os.path.join(os.path.dirname(__file__), '..', 'data', 'papers.db')
    LOG_PATH: str = os.path.join(os.path.dirname(__file__), '..', 'logs', 'system.log')
    
    @classmethod
    def validate(cls) -> List[str]:
        """設定項目のバリデーション
        
        戻り値:
            List[str]: バリデーションエラーメッセージのリスト（正常時は空）
        """
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY が必要です")
            
        if not cls.SENDER_EMAIL:
            errors.append("SENDER_EMAIL が必要です")
            
        if not cls.SENDER_PASSWORD:
            errors.append("SENDER_PASSWORD が必要です")
            
        if not cls.RECIPIENT_EMAILS:
            errors.append("RECIPIENT_EMAILS が必要です")
            
        if not cls.SEARCH_KEYWORDS:
            errors.append("SEARCH_KEYWORDS が必要です")
            
        if cls.MAX_PAPERS <= 0:
            errors.append("MAX_PAPERS は0より大きい値である必要があります")
            
        if cls.DAYS_BACK <= 0:
            errors.append("DAYS_BACK は0より大きい値である必要があります")
            
        return errors
    
    @classmethod
    def is_valid(cls) -> bool:
        """設定が有効かどうかをチェック
        
        戻り値:
            bool: 設定が有効な場合はTrue、そうでなければFalse
        """
        return len(cls.validate()) == 0