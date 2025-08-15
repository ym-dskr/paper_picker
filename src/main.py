#!/usr/bin/env python3
"""研究論文要約システムのメインエントリーポイント.

このモジュールは包括的なログ出力とエラーハンドリングを含む
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
    """アプリケーション用のログ設定.
    
    適切なフォーマットでファイルとコンソールの両方にログ出力を設定し、
    logsディレクトリの存在を確認します。
    
    Returns:
        設定されたロガーインスタンス
    """
    # プロジェクトルートのlogsディレクトリパスを取得
    project_root = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(project_root, 'logs')
    log_file = os.path.join(logs_dir, 'system.log')
    
    # logsディレクトリが存在しない場合は作成
    os.makedirs(logs_dir, exist_ok=True)
    
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def validate_system_requirements(config: Config) -> None:
    """システム要件と設定のバリデーション.
    
    Args:
        config: バリデーション対象の設定オブジェクト
        
    Raises:
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
    """設定に基づいてarXivから論文を取得.
    
    Args:
        fetcher: 論文取得インスタンス
        config: 設定オブジェクト
        
    Returns:
        取得された論文のリスト
        
    Raises:
        PaperFetchError: 論文取得が失敗した場合
    """
    logger = logging.getLogger(__name__)
    
    logger.info("論文検索を開始します...")
    try:
        # 大量の論文を取得してから関連度で絞り込む戦略
        # 初期収集数を大幅に増加（最終的に30件に絞り込み）
        initial_fetch_count = max(200, config.MAX_PAPERS * 10)  # 最低200件、通常は最終数の10倍
        
        logger.info(f"初期検索で{initial_fetch_count}件の論文を収集します...")
        all_papers = fetcher.fetch_arxiv_papers(
            config.SEARCH_KEYWORDS,
            max_results=initial_fetch_count
        )
        
        if not all_papers:
            logger.warning("新しい論文が見つかりませんでした")
            return []
        
        # 関連度と重要度の統計情報を表示
        if all_papers:
            avg_relevance = sum(p.get('relevance_score', 0) for p in all_papers) / len(all_papers)
            avg_importance = sum(p.get('importance_score', 0) for p in all_papers) / len(all_papers)
            high_relevance_count = sum(1 for p in all_papers if p.get('relevance_score', 0) >= 70)
            
            logger.info(
                f"合計{len(all_papers)}件の論文を発見しました "
                f"(関連度平均: {avg_relevance:.1f}, 重要度平均: {avg_importance:.1f}, "
                f"高関連度論文: {high_relevance_count}件)"
            )
        
        return all_papers
        
    except PaperFetchError as e:
        logger.error(f"論文取得に失敗しました: {e}")
        raise
    except Exception as e:
        logger.error(
            f"論文取得中に予期しないエラーが発生しました: {e}"
        )
        raise PaperFetchError(f"論文取得に失敗しました: {e}") from e


def filter_papers_by_keywords(
    papers: List[Dict],
    keywords: List[str]
) -> List[Dict]:
    """ユーザー設定キーワードに関連する論文のみをフィルタリング.
    
    Args:
        papers: フィルタリング対象の論文リスト
        keywords: ユーザー設定キーワード
        
    Returns:
        キーワードにマッチする論文のリスト
    """
    logger = logging.getLogger(__name__)
    
    if not papers:
        return []
    
    if not keywords:
        logger.info("キーワードが設定されていないため、全ての論文を要約対象にします")
        return papers
    
    logger.info(
        f"{len(papers)}件の論文をキーワード{keywords}でフィルタリングしています..."
    )
    
    filtered_papers = []
    for paper in papers:
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        text = f"{title} {abstract}"
        
        # いずれかのキーワードにマッチするかチェック
        for keyword in keywords:
            if keyword.lower() in text:
                filtered_papers.append(paper)
                break
    
    logger.info(
        f"キーワードフィルタリング結果: {len(filtered_papers)}/{len(papers)}件がマッチ"
    )
    
    return filtered_papers


def get_recency_score(published_date: str) -> float:
    """論文の新しさをスコア化（0-100）."""
    try:
        from datetime import datetime
        pub_date = datetime.strptime(published_date, '%Y-%m-%d')
        days_old = (datetime.now() - pub_date).days
        
        # 新しい論文ほど高いスコア
        if days_old <= 30:
            return 100.0
        elif days_old <= 90:
            return 90.0
        elif days_old <= 180:
            return 80.0
        elif days_old <= 365:
            return 70.0
        elif days_old <= 730:
            return 50.0
        else:
            return max(0.0, 50.0 - (days_old - 730) / 30)
            
    except (ValueError, TypeError):
        return 50.0


def select_balanced_papers(
    papers: List[Dict],
    max_papers: int,
    keywords: List[str]
) -> List[Dict]:
    """キーワードバランスを考慮して論文を選択.
    
    Args:
        papers: フィルタリング済み論文リスト
        max_papers: 選択する論文の最大数
        keywords: ユーザーキーワードリスト
        
    Returns:
        バランスよく選択された論文リスト
    """
    logger = logging.getLogger(__name__)
    
    if len(papers) <= max_papers:
        return papers
    
    if not keywords:
        return papers[:max_papers]
    
    # 各キーワードにマッチする論文を分類
    keyword_papers = {keyword: [] for keyword in keywords}
    unmatched_papers = []
    
    for paper in papers:
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        text = f"{title} {abstract}"
        
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in text:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            # 最初にマッチしたキーワードに分類
            keyword_papers[matched_keywords[0]].append(paper)
        else:
            unmatched_papers.append(paper)
    
    # 各キーワードから均等に選択
    papers_per_keyword = max(1, max_papers // len(keywords))
    selected_papers = []
    remaining_slots = max_papers
    
    for keyword in keywords:
        available_papers = keyword_papers[keyword]
        if available_papers and remaining_slots > 0:
            # 関連度、重要度、新しさを組み合わせてソート
            available_papers.sort(
                key=lambda x: (
                    x.get('relevance_score', 0) * 0.5 +    # 関連度50%
                    x.get('importance_score', 0) * 0.3 +   # 重要度30%
                    get_recency_score(x.get('published', '')) * 0.2  # 新しさ20%
                ), 
                reverse=True
            )
            take_count = min(papers_per_keyword, len(available_papers), remaining_slots)
            selected_papers.extend(available_papers[:take_count])
            remaining_slots -= take_count
            
            logger.debug(f"キーワード'{keyword}': {take_count}件選択（重要度考慮）")
    
    # 残りスロットがあれば、他の論文で埋める
    if remaining_slots > 0:
        remaining_papers = []
        for keyword_list in keyword_papers.values():
            remaining_papers.extend(keyword_list)
        remaining_papers.extend(unmatched_papers)
        
        # 既に選択済みの論文を除外
        selected_ids = {p.get('id') for p in selected_papers}
        additional_papers = [
            p for p in remaining_papers 
            if p.get('id') not in selected_ids
        ]
        
        # 関連度と重要度で残りスロットを埋める
        additional_papers.sort(
            key=lambda x: (
                x.get('relevance_score', 0) * 0.5 +    # 関連度50%
                x.get('importance_score', 0) * 0.3 +   # 重要度30%
                get_recency_score(x.get('published', '')) * 0.2  # 新しさ20%
            ),
            reverse=True
        )
        selected_papers.extend(additional_papers[:remaining_slots])
    
    # 選択された論文のスコア分布をログ出力
    if selected_papers:
        avg_relevance = sum(p.get('relevance_score', 0) for p in selected_papers) / len(selected_papers)
        avg_importance = sum(p.get('importance_score', 0) for p in selected_papers) / len(selected_papers)
        max_relevance = max(p.get('relevance_score', 0) for p in selected_papers)
        max_importance = max(p.get('importance_score', 0) for p in selected_papers)
        high_relevance_count = sum(1 for p in selected_papers if p.get('relevance_score', 0) >= 70)
        
        logger.info(
            f"選択論文スコア分布: "
            f"関連度平均{avg_relevance:.1f}(最高{max_relevance:.1f}), "
            f"重要度平均{avg_importance:.1f}(最高{max_importance:.1f}), "
            f"高関連度論文{high_relevance_count}件"
        )
    
    logger.info(f"キーワードバランスを考慮して{len(selected_papers)}件を選択しました")
    return selected_papers


def summarize_papers(
    summarizer: LLMSummarizer,
    papers: List[Dict],
    max_papers: int,
    keywords: List[str]
) -> List[Dict]:
    """キーワードにマッチする論文の要約を生成.
    
    Args:
        summarizer: 要約作成インスタンス
        papers: 要約対象の論文
        max_papers: 要約する論文の最大数
        keywords: ユーザー設定キーワード
        
    Returns:
        要約が追加された論文
        
    Raises:
        SummarizationError: 全ての論文で要約に失敗した場合
    """
    logger = logging.getLogger(__name__)
    
    # キーワードフィルタリング
    filtered_papers = filter_papers_by_keywords(papers, keywords)
    
    if not filtered_papers:
        logger.warning("キーワードにマッチする論文が見つかりませんでした")
        return []
    
    # キーワードバランスを考慮して論文を選択
    papers_to_summarize = select_balanced_papers(filtered_papers, max_papers, keywords)
    
    logger.info(
        f"キーワードマッチ論文{len(filtered_papers)}件から"
        f"上位{len(papers_to_summarize)}件を要約対象に選定"
    )
    
    logger.info(
        f"{len(papers_to_summarize)}件の論文の要約を開始します..."
    )
    
    try:
        summarized_papers = summarizer.batch_summarize(papers_to_summarize)
        
        # 少なくとも一部の要約が生成されたかチェック
        successful_summaries = sum(
            1 for p in summarized_papers 
            if p.get('summary_generated', False)
        )
        
        if successful_summaries == 0:
            raise SummarizationError("要約の生成に失敗しました")
        
        logger.info(
            f"要約処理が完了しました: "
            f"{successful_summaries}/{len(papers_to_summarize)}件成功"
        )
        return summarized_papers
        
    except Exception as e:
        logger.error(f"要約処理に失敗しました: {e}")
        raise


def save_to_database(db_manager: DatabaseManager, papers: List[Dict]) -> None:
    """論文をデータベースに保存.
    
    Args:
        db_manager: データベースマネージャーインスタンス
        papers: 保存対象の論文
        
    Raises:
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
    """結果を含むメール通知を送信.
    
    Args:
        email_sender: メール送信インスタンス
        summarized_papers: 要約付き論文
        all_papers: 発見された全論文
        
    Raises:
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
    """メインアプリケーションエントリーポイント.
    
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
        summarized_papers = summarize_papers(summarizer, all_papers, config.MAX_PAPERS, config.USER_KEYWORDS)
        save_to_database(db_manager, summarized_papers)
        send_notification(email_sender, summarized_papers, all_papers)
        
        # 最終統計の記録
        successful_summaries = sum(
            1 for p in summarized_papers
            if p.get('summary_generated', False)
        )
        
        logger.info("=== 処理完了 ===")
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