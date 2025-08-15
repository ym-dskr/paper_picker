"""研究論文システムの論文取得機能

このモジュールは、設定された検索条件とフィルタリングパラメータに
基づいてarXivから研究論文を取得する処理を行います。
"""

import arxiv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging


class PaperFetcher:
    """検索条件に基づいてarXivから研究論文を取得するクラス
    
    このクラスは、arXivからの論文取得を管理し、日付範囲、カテゴリ、
    キーワードのフィルタを適用しながら、適切なエラーハンドリングと
    重複除去を行います。
    
    属性:
        config: 検索パラメータを含む設定オブジェクト
        logger (logging.Logger): このクラス用のロガーインスタンス
    """
    
    def __init__(self, config) -> None:
        """論文取得クラスの初期化
        
        引数:
            config: 検索パラメータを含む設定オブジェクト
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def fetch_arxiv_papers(
        self, 
        keywords: List[str], 
        max_results: int = 10
    ) -> List[Dict]:
        """キーワードに基づいてarXivから研究論文を取得
        
        引数:
            keywords (List[str]): 検索キーワードのリスト
            max_results (int, optional): 返す論文の最大数。デフォルトは10
            
        戻り値:
            List[Dict]: メタデータ付きの論文辞書のリスト
            
        例外:
            PaperFetchError: 全てのキーワードで取得に失敗した場合
        """
        if not keywords:
            self.logger.warning("検索用のキーワードが提供されていません")
            return []
            
        papers = []
        successful_keywords = 0
        
        for keyword in keywords:
            try:
                keyword_papers = self._fetch_papers_for_keyword(
                    keyword.strip(), max_results
                )
                papers.extend(keyword_papers)
                successful_keywords += 1
                
            except Exception as e:
                self.logger.error(
                    f"キーワード'{keyword}'のarXiv検索に失敗しました: {e}"
                )
                continue
        
        if successful_keywords == 0:
            raise PaperFetchError("全てのキーワードで論文取得に失敗しました")
        
        # 重複除去と日付フィルタの適用
        unique_papers = self._remove_duplicates(papers)
        recent_papers = self._filter_recent_papers(unique_papers)
        
        self.logger.info(
            f"{successful_keywords}/{len(keywords)}個のキーワードから{len(recent_papers)}件の最新論文を取得しました"
        )
        
        return recent_papers[:max_results]
    
    def _fetch_papers_for_keyword(self, keyword: str, max_results: int) -> List[Dict]:
        """単一キーワードでの論文取得
        
        引数:
            keyword (str): 検索キーワード
            max_results (int): キーワードごとの最大取得数
            
        戻り値:
            List[Dict]: 論文辞書のリスト
        """
        # 電力・エネルギー・AI関連カテゴリの検索クエリを構築
        categories = [
            'cs.AI',        # 人工知能
            'cs.LG',        # 機械学習
            'cs.CV',        # コンピュータビジョン（衛星画像解析等）
            'cs.NE',        # ニューラル・進化計算
            'stat.ML',      # 統計的機械学習
            'eess.SP',      # 信号処理（予測・解析）
            'eess.SY',      # システムと制御（グリッド制御）
            'cs.SY',        # システムと制御
            'math.OC',      # 最適化と制御
            'stat.AP',      # 統計学応用（需要予測等）
            'cs.DC',        # 分散コンピューティング（スマートグリッド）
            'physics.soc-ph'  # 社会物理学（エネルギー市場）
        ]
        
        # 電力・エネルギー関連の重要キーワードを含む場合は優先的に検索
        power_keywords = [
            'power', 'energy', 'electricity', 'grid', 'renewable', 'solar', 'wind',
            'demand', 'forecast', 'prediction', 'smart grid', 'photovoltaic', 'battery',
            'storage', 'generation', 'load', 'voltage', 'frequency', 'stability'
        ]
        
        keyword_lower = keyword.lower()
        is_power_related = any(pk in keyword_lower for pk in power_keywords)
        
        if is_power_related:
            # 電力関連の場合はより広範囲のカテゴリで検索
            category_query = ' OR '.join(f'cat:{cat}' for cat in categories)
            query = f'({keyword}) AND ({category_query})'
        else:
            # AI・生成AI関連は主要カテゴリに絞る
            ai_categories = ['cs.AI', 'cs.LG', 'cs.CV', 'cs.NE', 'stat.ML']
            category_query = ' OR '.join(f'cat:{cat}' for cat in ai_categories)
            query = f'({keyword}) AND ({category_query})'
        
        search = arxiv.Search(
            query=query,
            max_results=max_results * 2,  # フィルタリングを考慮して余分に取得
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        papers = []
        for paper in search.results():
            paper_data = self._convert_arxiv_paper(paper, keyword)
            papers.append(paper_data)
                        
        return papers
    
    def _convert_arxiv_paper(self, paper, keyword: str) -> Dict:
        """arXiv論文オブジェクトを辞書形式に変換
        
        引数:
            paper: arXiv論文オブジェクト
            keyword (str): この論文を見つけた検索キーワード
            
        戻り値:
            Dict: 論文データ辞書
        """
        return {
            'id': paper.entry_id,
            'title': paper.title.strip(),
            'authors': [str(author).strip() for author in paper.authors],
            'abstract': paper.summary.strip(),
            'published': paper.published.strftime('%Y-%m-%d'),
            'pdf_url': paper.pdf_url,
            'categories': paper.categories,
            'keyword': keyword
        }
    
    def _filter_recent_papers(self, papers: List[Dict]) -> List[Dict]:
        """最新の論文のみにフィルタリング
        
        引数:
            papers (List[Dict]): 論文辞書のリスト
            
        戻り値:
            List[Dict]: フィルタリングされた最新論文のリスト
        """
        cutoff_date = datetime.now() - timedelta(days=self.config.DAYS_BACK)
        recent_papers = []
        
        for paper in papers:
            try:
                published_date = datetime.strptime(paper['published'], '%Y-%m-%d')
                if published_date >= cutoff_date:
                    recent_papers.append(paper)
            except (ValueError, KeyError) as e:
                self.logger.warning(f"論文{paper.get('id', 'unknown')}の日付形式が無効です: {e}")
                continue
                
        return recent_papers
    
    def _remove_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """論文IDに基づく重複論文の除去
        
        引数:
            papers (List[Dict]): 論文辞書のリスト
            
        戻り値:
            List[Dict]: 重複が除去されたリスト
        """
        seen_ids = set()
        unique_papers = []
        duplicate_count = 0
        
        for paper in papers:
            paper_id = paper.get('id')
            if not paper_id:
                self.logger.warning("IDが欠けている論文をスキップします")
                continue
                
            if paper_id not in seen_ids:
                seen_ids.add(paper_id)
                unique_papers.append(paper)
            else:
                duplicate_count += 1
        
        if duplicate_count > 0:
            self.logger.info(f"{duplicate_count}件の重複論文を除去しました")
        
        return unique_papers


class PaperFetchError(Exception):
    """論文取得エラー用のカスタム例外"""
    pass