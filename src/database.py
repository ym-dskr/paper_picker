"""論文ピッカーシステムのデータベース管理

このモジュールは、SQLiteを使用した研究論文情報の
保存と取得に関するデータベース操作を提供します。
"""

import sqlite3
import os
from typing import List, Dict, Optional
import logging
from datetime import datetime


class DatabaseManager:
    """研究論文のSQLiteデータベース操作を管理するクラス
    
    このクラスは、テーブル作成、論文保存、検索などの
    全てのデータベース操作を適切なエラーハンドリングと
    ログ出力とともに処理します。
    
    属性:
        db_path (str): SQLiteデータベースファイルのパス
        logger (logging.Logger): このクラス用のロガーインスタンス
    """
    
    def __init__(self, db_path: str) -> None:
        """データベースマネージャーの初期化
        
        引数:
            db_path (str): SQLiteデータベースファイルのパス
            
        例外:
            DatabaseError: データベース初期化が失敗した場合
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()

    def _init_database(self) -> None:
        """データベースの初期化とテーブル作成
        
        存在しない場合はディレクトリ構造を作成し、
        必要なスキーマでpapersテーブルを初期化します。
        
        例外:
            DatabaseError: データベース初期化が失敗した場合
        """
        try:
            # ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS papers (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        authors TEXT,
                        abstract TEXT,
                        summary_ja TEXT,
                        published DATE,
                        pdf_url TEXT,
                        categories TEXT,
                        keyword TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                self.logger.info("データベースの初期化が完了しました")
                
        except Exception as e:
            error_msg = f"データベース初期化に失敗しました: {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def save_papers(self, papers: List[Dict]) -> bool:
        """論文データをデータベースに保存
        
        引数:
            papers (List[Dict]): 保存する論文辞書のリスト
            
        戻り値:
            bool: 全ての論文が正常に保存された場合はTrue、そうでなければFalse
            
        例外:
            DatabaseError: データベース操作が失敗した場合
        """
        if not papers:
            self.logger.warning("保存する論文データが提供されていません")
            return True
            
        try:
            # ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                for paper in papers:
                    # 必要なフィールドのバリデーション
                    if not self._validate_paper_data(paper):
                        self.logger.warning(f"無効な論文データをスキップします: {paper.get('id', 'unknown')}")
                        continue
                        
                    conn.execute('''
                        INSERT OR REPLACE INTO papers 
                        (id, title, authors, abstract, summary_ja, published, 
                         pdf_url, categories, keyword)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        paper['id'],
                        paper['title'],
                        ', '.join(paper.get('authors', [])),
                        paper.get('abstract', ''),
                        paper.get('summary_ja', ''),
                        paper.get('published', ''),
                        paper.get('pdf_url', ''),
                        ', '.join(paper.get('categories', [])),
                        paper.get('keyword', '')
                    ))
                    
                conn.commit()
                self.logger.info(f"データベース保存が完了しました: {len(papers)}件の論文")
                return True
                
        except Exception as e:
            error_msg = f"データベース保存に失敗しました: {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg) from e

    def get_recent_papers(self, days: int = 30) -> List[Dict]:
        """最近処理された論文をデータベースから取得
        
        引数:
            days (int, optional): 何日前まで遡るか。デフォルトは30日
            
        戻り値:
            List[Dict]: 論文辞書のリスト、見つからない場合やエラー時は空リスト
            
        例外:
            DatabaseError: データベース操作が失敗した場合
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # SQLインジェクション対策のためパラメータ化クエリを使用
                cursor = conn.execute('''
                    SELECT * FROM papers 
                    WHERE DATE(processed_at) >= DATE('now', ? || ' days')
                    ORDER BY processed_at DESC
                ''', (f'-{days}',))
                
                papers = []
                for row in cursor.fetchall():
                    papers.append({
                        'id': row[0],
                        'title': row[1],
                        'authors': row[2].split(', ') if row[2] else [],
                        'abstract': row[3] or '',
                        'summary_ja': row[4] or '',
                        'published': row[5] or '',
                        'pdf_url': row[6] or '',
                        'categories': row[7].split(', ') if row[7] else [],
                        'keyword': row[8] or '',
                        'processed_at': row[9]
                    })
                
                self.logger.info(f"過去{days}日間の{len(papers)}件の論文を取得しました")
                return papers
                
        except Exception as e:
            error_msg = f"データベース読み取りに失敗しました: {e}"
            self.logger.error(error_msg)
            raise DatabaseError(error_msg) from e
    
    def _validate_paper_data(self, paper: Dict) -> bool:
        """保存前の論文データのバリデーション
        
        引数:
            paper (Dict): 論文データ辞書
            
        戻り値:
            bool: データが有効な場合はTrue、そうでなければFalse
        """
        required_fields = ['id', 'title']
        
        for field in required_fields:
            if field not in paper or not paper[field]:
                self.logger.warning(f"論文データに必須フィールド'{field}'がありません")
                return False
                
        return True
    
    def paper_exists(self, paper_id: str) -> bool:
        """指定されたIDの論文がデータベースに存在するかチェック
        
        引数:
            paper_id (str): 論文の一意識別子
            
        戻り値:
            bool: 論文が存在する場合はTrue、そうでなければFalse
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT COUNT(*) FROM papers WHERE id = ?',
                    (paper_id,)
                )
                count = cursor.fetchone()[0]
                return count > 0
                
        except Exception as e:
            self.logger.error(f"論文存在確認エラー: {e}")
            return False


class DatabaseError(Exception):
    """データベース関連エラー用のカスタム例外"""
    pass