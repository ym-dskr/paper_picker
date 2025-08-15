#!/usr/bin/env python3
import logging
import sys
import os
from datetime import datetime

# 自作モジュールのインポート
from config import Config
from paper_fetcher import PaperFetcher
from llm_summarizer import LLMSummarizer
from email_sender import EmailSender
from database import DatabaseManager

def setup_logging():
    """ログ設定"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/system.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """メイン処理"""
    logger = logging.getLogger(__name__)
    logger.info("=== 論文要約システム開始 ===")
    
    try:
        # 設定読み込み
        config = Config()
        
        # 各モジュール初期化
        fetcher = PaperFetcher(config)
        summarizer = LLMSummarizer(config)
        email_sender = EmailSender(config)
        db_manager = DatabaseManager(config.DB_PATH)
        
        # 論文取得
        logger.info("論文検索開始...")
        papers = fetcher.fetch_arxiv_papers(config.SEARCH_KEYWORDS, config.MAX_PAPERS)
        
        if not papers:
            logger.info("新しい論文が見つかりませんでした")
            return
        
        # LLM要約生成
        logger.info(f"要約生成開始... ({len(papers)}件)")
        summarized_papers = []
        for i, paper in enumerate(papers, 1):
            logger.info(f"要約生成中: {i}/{len(papers)} - {paper['title'][:50]}...")
            summarized_paper = summarizer.summarize_paper(paper)
            summarized_papers.append(summarized_paper)
        
        # データベース保存
        db_manager.save_papers(summarized_papers)
        
        # メール送信
        logger.info("メール送信開始...")
        success = email_sender.send_summary_email(summarized_papers)
        
        if success:
            logger.info("=== 処理完了 ===")
        else:
            logger.error("メール送信に失敗しました")
            
    except Exception as e:
        logger.error(f"システムエラー: {e}")
        raise

if __name__ == "__main__":
    setup_logging()
    main()