#!/usr/bin/env python3
"""研究論文要約システムのメインエントリーポイント

このモジュールは、包括的なログ出力とエラーハンドリングを含む
論文収集、要約、通知の全体パイプラインを統括します。
"""

import logging
import sys
import os
from datetime import datetime
from typing import List, Dict

# カスタムモジュールのインポート
from config import Config
from paper_fetcher import PaperFetcher, PaperFetchError
from llm_summarizer import LLMSummarizer, SummarizationError
from email_sender import EmailSender, EmailError
from database import DatabaseManager, DatabaseError


def setup_logging() -> logging.Logger:
    """アプリケーション用のログ設定
    
    適切なフォーマットでファイルとコンソールの両方にログ出力を設定し、
    logsディレクトリの存在を確認します。
    
    戻り値:
        logging.Logger: 設定されたロガーインスタンス
    """
    # logsディレクトリが存在しない場合は作成
    os.makedirs('logs', exist_ok=True)
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/system.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def validate_system_requirements(config: Config) -> None:
    """システム要件と設定のバリデーション
    
    引数:
        config (Config): バリデーション対象の設定オブジェクト
        
    例外:
        SystemExit: 重要な要件が満たされていない場合
    """
    logger = logging.getLogger(__name__)
    
    # 設定のバリデーション
    config_errors = config.validate()
    if config_errors:
        logger.error("設定バリデーションに失敗しました:")
        for error in config_errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info("システム要件バリデーションに合格しました")


def fetch_papers(fetcher: PaperFetcher, config: Config) -> List[Dict]:
    """設定に基づいてarXivから論文を取得
    
    引数:
        fetcher (PaperFetcher): 論文取得インスタンス
        config (Config): 設定オブジェクト
        
    戻り値:
        List[Dict]: 取得された論文のリスト
        
    例外:
        PaperFetchError: 論文取得が失敗した場合
    """
    logger = logging.getLogger(__name__)
    
    logger.info("論文検索を開始します...")
    try:
        # 良い選択肢を得るため、最初により多くの論文を取得
        all_papers = fetcher.fetch_arxiv_papers(
            config.SEARCH_KEYWORDS, 
            max_results=100
        )
        
        if not all_papers:
            logger.warning("新しい論文が見つかりませんでした")
            return []
        
        logger.info(f"合計{len(all_papers)}件の論文を発見しました")
        return all_papers
        
    except PaperFetchError as e:
        logger.error(f"論文取得に失敗しました: {e}")
        raise
    except Exception as e:
        logger.error(f"論文取得中に予期しないエラーが発生しました: {e}")
        raise PaperFetchError(f"論文取得に失敗しました: {e}") from e


def summarize_papers(
    summarizer: LLMSummarizer, 
    papers: List[Dict], 
    max_papers: int
) -> List[Dict]:
    """選択された論文の要約を生成
    
    引数:
        summarizer (LLMSummarizer): 要約作成インスタンス
        papers (List[Dict]): 要約対象の論文
        max_papers (int): 要約する論文の最大数
        
    戻り値:
        List[Dict]: 要約が追加された論文
        
    例外:
        SummarizationError: 全ての論文で要約に失敗した場合
    """
    logger = logging.getLogger(__name__)
    
    # 要約対象論文の選択（max_papersに制限）
    papers_to_summarize = papers[:max_papers]
    
    logger.info(f"{len(papers_to_summarize)}件の論文の要約を開始します...")
    
    try:
        summarized_papers = summarizer.batch_summarize(papers_to_summarize)
        
        # 少なくとも一部の要約が生成されたかチェック
        successful_summaries = sum(
            1 for p in summarized_papers 
            if p.get('summary_generated', False)
        )
        
        if successful_summaries == 0:
            raise SummarizationError("要約の生成に失敗しました")
        
        logger.info(f"要約処理が完了しました: {successful_summaries}/{len(papers_to_summarize)}件成功")
        return summarized_papers
        
    except Exception as e:
        logger.error(f"要約処理に失敗しました: {e}")
        raise


def save_to_database(db_manager: DatabaseManager, papers: List[Dict]) -> None:
    """論文をデータベースに保存
    
    引数:
        db_manager (DatabaseManager): データベースマネージャーインスタンス
        papers (List[Dict]): 保存対象の論文
        
    例外:
        DatabaseError: データベース操作が失敗した場合
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("論文をデータベースに保存します...")
        success = db_manager.save_papers(papers)
        
        if success:
            logger.info("データベース保存が正常に完了しました")
        else:
            logger.warning("データベース保存は警告付きで完了しました")
            
    except DatabaseError as e:
        logger.error(f"データベース保存に失敗しました: {e}")
        raise
    except Exception as e:
        logger.error(f"予期しないデータベースエラー: {e}")
        raise DatabaseError(f"データベース操作に失敗しました: {e}") from e


def send_notification(
    email_sender: EmailSender, 
    summarized_papers: List[Dict], 
    all_papers: List[Dict]
) -> None:
    """結果を含むメール通知を送信
    
    引数:
        email_sender (EmailSender): メール送信インスタンス
        summarized_papers (List[Dict]): 要約付き論文
        all_papers (List[Dict]): 発見された全論文
        
    例外:
        EmailError: メール送信が失敗した場合
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("メール通知を送信します...")
        success = email_sender.send_summary_email(summarized_papers, all_papers)
        
        if success:
            logger.info("メール通知が正常に送信されました")
        else:
            raise EmailError("メール送信に失敗しました")
            
    except Exception as e:
        logger.error(f"メール通知に失敗しました: {e}")
        raise EmailError(f"メール送信に失敗しました: {e}") from e


def main() -> None:
    """メインアプリケーションエントリーポイント
    
    包括的なエラーハンドリングとログ出力を含む
    論文処理パイプライン全体を統括します。
    """
    logger = setup_logging()
    logger.info("=== 研究論文要約システムを開始しました ===")
    
    try:
        # 設定の読み込みとバリデーション
        logger.info("設定を読み込んでいます...")
        config = Config()
        validate_system_requirements(config)
        
        # コンポーネントの初期化
        logger.info("システムコンポーネントを初期化しています...")
        fetcher = PaperFetcher(config)
        summarizer = LLMSummarizer(config)
        email_sender = EmailSender(config)
        db_manager = DatabaseManager(config.DB_PATH)
        
        # メインパイプラインの実行
        all_papers = fetch_papers(fetcher, config)
        
        if not all_papers:
            logger.info("処理する論文がないため、空の通知を送信します")
            send_notification(email_sender, [], [])
            return
        
        # 論文処理
        summarized_papers = summarize_papers(summarizer, all_papers, config.MAX_PAPERS)
        save_to_database(db_manager, summarized_papers)
        send_notification(email_sender, summarized_papers, all_papers)
        
        # 最終統計の記録
        successful_summaries = sum(
            1 for p in summarized_papers 
            if p.get('summary_generated', False)
        )
        
        logger.info(f"=== 処理完了 ===")
        logger.info(f"発見論文総数: {len(all_papers)}")
        logger.info(f"要約済み論文: {len(summarized_papers)}")
        logger.info(f"成功した要約: {successful_summaries}")
        
    except (PaperFetchError, SummarizationError, DatabaseError, EmailError) as e:
        logger.error(f"アプリケーションエラー: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("ユーザーによってアプリケーションが中断されました")
        sys.exit(0)
    except Exception as e:
        logger.error(f"予期しないシステムエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()