"""論文ピッカーシステムの設定管理モジュール.

このモジュールは研究論文要約システムの全ての設定を管理します。
APIキー、メール設定、検索パラメータなどを含みます。
"""

import os
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()


class Config:
    """論文ピッカーシステムの設定クラス.
    
    環境変数から読み込まれた設定を管理し、適切なデフォルト値と
    バリデーションを提供します。
    
    Attributes:
        OPENAI_API_KEY: LLMサービス用のOpenAI APIキー
        SMTP_SERVER: メール送信用のSMTPサーバーホスト名
        SMTP_PORT: SMTPサーバーのポート番号
        SENDER_EMAIL: 通知メール送信用のメールアドレス
        SENDER_PASSWORD: メール認証用のパスワード
        RECIPIENT_EMAILS: 受信者メールアドレスのリスト
        MAX_PAPERS: 要約対象論文の最大数
        SEARCH_KEYWORDS: 論文検索用のキーワードリスト
        USER_KEYWORDS: 要約対象をフィルタリングするユーザーキーワード
        DAYS_BACK: 検索対象期間（日数）
        DB_PATH: SQLiteデータベースファイルのパス
        LOG_PATH: ログファイルのパス
    """
    
    # OpenAI設定
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    
    # メール設定
    SMTP_SERVER: str = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL: Optional[str] = os.getenv('SENDER_EMAIL')
    SENDER_PASSWORD: Optional[str] = os.getenv('SENDER_PASSWORD')
    RECIPIENT_EMAILS: List[str] = [
        email.strip() 
        for email in os.getenv('RECIPIENT_EMAILS', '').split(',')
        if email.strip()
    ]
    
    # 検索設定
    MAX_PAPERS: int = int(os.getenv('MAX_PAPERS', '10'))
    SEARCH_KEYWORDS: List[str] = [
        keyword.strip() 
        for keyword in os.getenv('SEARCH_KEYWORDS', '').split(',')
        if keyword.strip()
    ]
    
    # ユーザーキーワード設定（要約対象をフィルタリング）
    # 空リストの場合は全ての論文が要約対象になります
    USER_KEYWORDS: List[str] = [
        'prediction',  # 予測関連
        'wind',        # 風力発電
        'Photovoltaic', # 太陽光発電  
        'offshore',    # 洋上風力
        'deep learning', # 深層学習
        'machine learning', # 機械学習
        'llm', # LLM
    ]
    
    # 日付範囲設定
    DATE_SEARCH_MODE: str = os.getenv('DATE_SEARCH_MODE', 'days_back')
    DAYS_BACK: int = int(os.getenv('DAYS_BACK', '7'))
    START_DATE: Optional[str] = os.getenv('START_DATE')
    END_DATE: Optional[str] = os.getenv('END_DATE')
    
    # ファイルパス
    DB_PATH: str = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'papers.db'
    )
    LOG_PATH: str = os.path.join(
        os.path.dirname(__file__), '..', 'logs', 'system.log'
    )
    
    @classmethod
    def validate(cls) -> List[str]:
        """設定項目のバリデーション.
        
        Returns:
            バリデーションエラーメッセージのリスト（正常時は空）
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
            
        # 日付設定のバリデーション
        if cls.DATE_SEARCH_MODE not in ['days_back', 'date_range']:
            errors.append(
                "DATE_SEARCH_MODE は 'days_back' または 'date_range' である必要があります"
            )
        
        if cls.DATE_SEARCH_MODE == 'days_back':
            if cls.DAYS_BACK <= 0:
                errors.append("DAYS_BACK は0より大きい値である必要があります")
        
        elif cls.DATE_SEARCH_MODE == 'date_range':
            if not cls.START_DATE:
                errors.append("DATE_SEARCH_MODE='date_range'の場合、START_DATEが必要です")
            if not cls.END_DATE:
                errors.append("DATE_SEARCH_MODE='date_range'の場合、END_DATEが必要です")
            
            # 日付形式の検証
            if cls.START_DATE:
                try:
                    datetime.strptime(cls.START_DATE, '%Y-%m-%d')
                except ValueError:
                    errors.append("START_DATEはYYYY-MM-DD形式で指定してください")
            
            if cls.END_DATE:
                try:
                    datetime.strptime(cls.END_DATE, '%Y-%m-%d')
                except ValueError:
                    errors.append("END_DATEはYYYY-MM-DD形式で指定してください")
            
        return errors
    
    @classmethod
    def is_valid(cls) -> bool:
        """設定が有効かどうかをチェック.
        
        Returns:
            設定が有効な場合はTrue、そうでなければFalse
        """
        return len(cls.validate()) == 0
    
    @classmethod
    def get_date_range(cls) -> Tuple[datetime, datetime]:
        """設定に基づいて検索日付範囲を取得.
        
        Returns:
            検索開始日と終了日のタプル（UTC datetime）
            
        Raises:
            ValueError: 日付設定が無効な場合
        """
        if cls.DATE_SEARCH_MODE == 'days_back':
            # 現在から指定日数分さかのぼる
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=cls.DAYS_BACK)
            return start_date, end_date
            
        elif cls.DATE_SEARCH_MODE == 'date_range':
            # 指定された日付範囲を使用
            if not cls.START_DATE or not cls.END_DATE:
                raise ValueError(
                    "DATE_SEARCH_MODE='date_range'の場合、START_DATEとEND_DATEが必要です"
                )
            
            try:
                start_date = datetime.strptime(cls.START_DATE, '%Y-%m-%d')
                end_date = datetime.strptime(cls.END_DATE, '%Y-%m-%d')
                
                # 終了日は23:59:59まで含める
                end_date = end_date.replace(hour=23, minute=59, second=59)
                
                if start_date > end_date:
                    raise ValueError("START_DATEはEND_DATEより前の日付である必要があります")
                    
                return start_date, end_date
                
            except ValueError as e:
                if "time data" in str(e):
                    raise ValueError(
                        "日付はYYYY-MM-DD形式で指定してください（例: 2024-01-15）"
                    ) from e
                raise
                
        else:
            raise ValueError(
                f"無効なDATE_SEARCH_MODE: {cls.DATE_SEARCH_MODE}. "
                "'days_back'または'date_range'を指定してください"
            )