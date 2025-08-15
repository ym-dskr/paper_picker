import sqlite3
from typing import List, Dict
import logging
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """データベース初期化"""
        try:
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
                self.logger.info("データベース初期化完了")
        except Exception as e:
            self.logger.error(f"データベース初期化エラー: {e}")
    
    def save_papers(self, papers: List[Dict]):
        """論文データを保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for paper in papers:
                    conn.execute('''
                        INSERT OR REPLACE INTO papers 
                        (id, title, authors, abstract, summary_ja, published, 
                         pdf_url, categories, keyword)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        paper['id'],
                        paper['title'],
                        ', '.join(paper['authors']),
                        paper['abstract'],
                        paper.get('summary_ja', ''),
                        paper['published'],
                        paper['pdf_url'],
                        ', '.join(paper['categories']),
                        paper['keyword']
                    ))
                conn.commit()
                self.logger.info(f"データベース保存完了: {len(papers)}件")
        except Exception as e:
            self.logger.error(f"データベース保存エラー: {e}")
    
    def get_recent_papers(self, days: int = 30) -> List[Dict]:
        """最近の論文を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM papers 
                    WHERE DATE(processed_at) >= DATE('now', '-{} days')
                    ORDER BY processed_at DESC
                '''.format(days))
                
                papers = []
                for row in cursor.fetchall():
                    papers.append({
                        'id': row[0],
                        'title': row[1],
                        'authors': row[2].split(', ') if row[2] else [],
                        'abstract': row[3],
                        'summary_ja': row[4],
                        'published': row[5],
                        'pdf_url': row[6],
                        'categories': row[7].split(', ') if row[7] else [],
                        'keyword': row[8],
                        'processed_at': row[9]
                    })
                
                return papers
        except Exception as e:
            self.logger.error(f"データベース読み取りエラー: {e}")
            return []