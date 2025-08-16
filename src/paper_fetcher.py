"""研究論文システムの論文取得機能モジュール.

このモジュールは設定された検索条件とフィルタリングパラメータに
基づいてarXivから研究論文を取得する処理を行います。
"""

import arxiv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import re
import math


class PaperFetcher:
    """検索条件に基づいてarXivから研究論文を取得するクラス.
    
    このクラスはarXivからの論文取得を管理し、日付範囲、カテゴリ、
    キーワードのフィルタを適用しながら、適切なエラーハンドリングと
    重複除去を行います。
    
    Attributes:
        config: 検索パラメータを含む設定オブジェクト
        logger: このクラス用のロガーインスタンス
    """
    
    def __init__(self, config) -> None:
        """論文取得クラスの初期化.
        
        Args:
            config: 検索パラメータを含む設定オブジェクト
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def fetch_arxiv_papers(
        self,
        keywords: List[str],
        max_results: int = 10
    ) -> List[Dict]:
        """キーワードに基づいてarXivから研究論文を取得.
        
        Args:
            keywords: 検索キーワードのリスト
            max_results: 返す論文の最大数。デフォルトは10
            
        Returns:
            メタデータ付きの論文辞書のリスト
            
        Raises:
            PaperFetchError: 全てのキーワードで取得に失敗した場合
        """
        if not keywords:
            self.logger.warning("検索用のキーワードが提供されていません")
            return []
        
        # バランスよく論文を取得するための戦略
        return self._fetch_papers_with_balanced_keywords(keywords, max_results)
    
    def _fetch_papers_with_balanced_keywords(
        self, 
        keywords: List[str], 
        max_results: int
    ) -> List[Dict]:
        """キーワード間でバランスよく論文を取得.
        
        Args:
            keywords: 検索キーワードのリスト
            max_results: 返す論文の最大数
            
        Returns:
            バランスよく取得された論文のリスト
        """
        # 各キーワードから取得すべき論文数を計算（最低1件は確保）
        papers_per_keyword = max(1, max_results // len(keywords))
        extra_papers = max_results % len(keywords)
        
        all_keyword_papers = {}
        successful_keywords = 0
        
        self.logger.info(
            f"各キーワードから{papers_per_keyword}件ずつ論文を取得します"
        )
        
        # 各キーワードから個別に論文を取得
        for i, keyword in enumerate(keywords):
            try:
                # 最初の数個のキーワードには余分な論文を割り当て
                target_count = papers_per_keyword + (1 if i < extra_papers else 0)
                # 関連度フィルタリングを前提に大量取得（最大100件/キーワード）
                fetch_count = min(100, target_count * 5)  # 5倍取得して関連度で絞り込み
                keyword_papers = self._fetch_papers_for_keyword(
                    keyword.strip(), fetch_count
                )
                
                if keyword_papers:
                    all_keyword_papers[keyword] = keyword_papers
                    successful_keywords += 1
                    self.logger.info(
                        f"キーワード'{keyword}': {len(keyword_papers)}件取得"
                    )
                else:
                    self.logger.warning(f"キーワード'{keyword}'で論文が見つかりませんでした")
                
            except Exception as e:
                self.logger.error(
                    f"キーワード'{keyword}'のarXiv検索に失敗しました: {e}"
                )
                continue
        
        if successful_keywords == 0:
            raise PaperFetchError("全てのキーワードで論文取得に失敗しました")
        
        # 多段階フィルタリングシステムを適用
        filtered_papers = self._apply_multi_stage_filtering(
            all_keyword_papers, max_results
        )
        
        self.logger.info(
            f"{successful_keywords}/{len(keywords)}個のキーワードから"
            f"多段階フィルタリングで{len(filtered_papers)}件の高関連度論文を取得しました"
        )
        
        return filtered_papers
    
    def _apply_multi_stage_filtering(
        self, 
        keyword_papers: Dict[str, List[Dict]], 
        max_results: int
    ) -> List[Dict]:
        """多段階フィルタリングシステムで高関連度論文を抽出.
        
        Args:
            keyword_papers: キーワード別論文辞書
            max_results: 最終出力数
            
        Returns:
            多段階フィルタリング済み論文リスト
        """
        if not keyword_papers:
            return []
        
        # Stage 1: 全論文を収集
        all_papers = []
        for keyword, papers in keyword_papers.items():
            all_papers.extend(papers)
        
        self.logger.info(f"Stage 1: 全{len(all_papers)}件の論文を収集")
        
        # Stage 2: 重複除去
        unique_papers = self._remove_duplicates(all_papers)
        self.logger.info(f"Stage 2: 重複除去後{len(unique_papers)}件")
        
        # Stage 3: 日付フィルタ
        recent_papers = self._filter_recent_papers(unique_papers)
        self.logger.info(f"Stage 3: 日付フィルタ後{len(recent_papers)}件")
        
        # Stage 4: 関連度による第1次絞り込み（上位30-50%を残す）
        stage4_target = max(max_results * 3, min(100, len(recent_papers)))
        relevance_filtered = self._filter_by_relevance_score(recent_papers, stage4_target)
        self.logger.info(f"Stage 4: 関連度フィルタ後{len(relevance_filtered)}件")
        
        # Stage 5: 重要度と関連度の組み合わせによる第2次絞り込み
        stage5_target = max(max_results * 2, min(50, len(relevance_filtered)))
        combined_filtered = self._filter_by_combined_score(relevance_filtered, stage5_target)
        self.logger.info(f"Stage 5: 複合スコアフィルタ後{len(combined_filtered)}件")
        
        # Stage 6: キーワードバランスを考慮した最終選択
        final_papers = self._final_balanced_selection(combined_filtered, max_results)
        self.logger.info(f"Stage 6: 最終選択{len(final_papers)}件")
        
        return final_papers
    
    def _filter_by_relevance_score(
        self, 
        papers: List[Dict], 
        target_count: int,
        min_score: float = 30.0
    ) -> List[Dict]:
        """関連度スコアによる論文フィルタリング."""
        # 関連度スコア順にソート
        sorted_papers = sorted(
            papers, 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )
        
        # 最低スコア基準も適用
        filtered_papers = [
            p for p in sorted_papers 
            if p.get('relevance_score', 0) >= min_score
        ]
        
        # 目標数まで絞り込み
        return filtered_papers[:target_count]
    
    def _filter_by_combined_score(
        self, 
        papers: List[Dict], 
        target_count: int
    ) -> List[Dict]:
        """重要度と関連度を組み合わせたスコアによる論文フィルタリング."""
        # 複合スコア = 関連度60% + 重要度30% + 新しさ10%
        for paper in papers:
            relevance = paper.get('relevance_score', 0)
            importance = paper.get('importance_score', 0)
            recency = self._get_recency_score(paper.get('published', ''))
            
            combined_score = (
                relevance * 0.6 + 
                importance * 0.3 + 
                recency * 0.1
            )
            paper['combined_score'] = combined_score
        
        # 複合スコア順にソート
        sorted_papers = sorted(
            papers, 
            key=lambda x: x.get('combined_score', 0), 
            reverse=True
        )
        
        return sorted_papers[:target_count]
    
    def _final_balanced_selection(
        self, 
        papers: List[Dict], 
        max_results: int
    ) -> List[Dict]:
        """キーワードバランスを考慮した最終選択."""
        if len(papers) <= max_results:
            return papers
        
        if not hasattr(self.config, 'USER_KEYWORDS') or not self.config.USER_KEYWORDS:
            # USER_KEYWORDSが設定されていない場合は複合スコア順
            return sorted(papers, key=lambda x: x.get('combined_score', 0), reverse=True)[:max_results]
        
        # USER_KEYWORDSを基準にバランス選択
        keyword_papers = {keyword: [] for keyword in self.config.USER_KEYWORDS}
        unmatched_papers = []
        
        # 各論文をUSER_KEYWORDSでグループ化
        for paper in papers:
            title = paper.get('title', '').lower()
            abstract = paper.get('abstract', '').lower()
            text = f"{title} {abstract}"
            
            best_match = None
            best_score = 0
            
            for keyword in self.config.USER_KEYWORDS:
                if keyword.lower() in text:
                    # 複数マッチの場合は関連度が高い方を選択
                    current_score = self._calculate_keyword_match_score(text, [keyword])
                    if current_score > best_score:
                        best_match = keyword
                        best_score = current_score
            
            if best_match:
                keyword_papers[best_match].append(paper)
            else:
                unmatched_papers.append(paper)
        
        # 各キーワードから均等に選択
        papers_per_keyword = max_results // len(self.config.USER_KEYWORDS)
        selected_papers = []
        remaining_slots = max_results
        
        for keyword in self.config.USER_KEYWORDS:
            available_papers = keyword_papers[keyword]
            if available_papers and remaining_slots > 0:
                # 複合スコア順にソート
                available_papers.sort(
                    key=lambda x: x.get('combined_score', 0), 
                    reverse=True
                )
                take_count = min(papers_per_keyword, len(available_papers), remaining_slots)
                selected_papers.extend(available_papers[:take_count])
                remaining_slots -= take_count
                
                self.logger.debug(f"キーワード'{keyword}': {take_count}件選択")
        
        # 残りスロットを未分類論文で埋める
        if remaining_slots > 0 and unmatched_papers:
            unmatched_papers.sort(
                key=lambda x: x.get('combined_score', 0), 
                reverse=True
            )
            selected_papers.extend(unmatched_papers[:remaining_slots])
        
        return selected_papers
    
    def _balance_papers_by_keyword(
        self, 
        keyword_papers: Dict[str, List[Dict]], 
        max_results: int
    ) -> List[Dict]:
        """キーワード別に取得した論文をバランスよく選択.
        
        Args:
            keyword_papers: キーワード別の論文辞書
            max_results: 最大結果数
            
        Returns:
            バランスよく選択された論文のリスト
        """
        if not keyword_papers:
            return []
        
        balanced_papers = []
        keywords = list(keyword_papers.keys())
        papers_per_keyword = max_results // len(keywords)
        extra_papers = max_results % len(keywords)
        
        # 各キーワードから重要度を考慮して論文を選択
        for i, keyword in enumerate(keywords):
            papers = keyword_papers[keyword]
            target_count = papers_per_keyword + (1 if i < extra_papers else 0)
            
            # 重要度スコアと新しさの組み合わせでソート
            papers.sort(
                key=lambda x: (
                    x.get('importance_score', 0) * 0.7 +  # 重要度70%
                    self._get_recency_score(x.get('published', '')) * 0.3  # 新しさ30%
                ), 
                reverse=True
            )
            selected_papers = papers[:target_count]
            balanced_papers.extend(selected_papers)
            
            self.logger.debug(
                f"キーワード'{keyword}'から重要度順に{len(selected_papers)}件選択"
            )
        
        return balanced_papers
    
    def _fetch_papers_for_keyword(self, keyword: str, max_results: int) -> List[Dict]:
        """単一キーワードでの論文取得（日付範囲を考慮したキーワード検索）.
        
        Args:
            keyword: 検索キーワード
            max_results: キーワードごとの最大取得数
            
        Returns:
            論文辞書のリスト
        """
        try:
            # 設定から日付範囲を取得
            start_date, end_date = self.config.get_date_range()
            self.logger.info(
                f"キーワード'{keyword}': {start_date.strftime('%Y-%m-%d')} ～ "
                f"{end_date.strftime('%Y-%m-%d')} の期間で検索"
            )
            
            # シンプルなキーワード検索（タイトル、アブストラクト、カテゴリのいずれかに含まれる）
            query = f'all:{keyword}'
            
            search = arxiv.Search(
                query=query,
                max_results=max_results * 3,  # 日付フィルタリングを考慮して余分に取得
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            for paper in search.results():
                # 日付範囲チェック
                if self._is_paper_in_date_range(paper, start_date, end_date):
                    paper_data = self._convert_arxiv_paper(paper, keyword)
                    papers.append(paper_data)
                    
                    # 必要な件数に達したら終了
                    if len(papers) >= max_results:
                        break
                        
            return papers
            
        except ValueError as e:
            self.logger.error(f"日付設定エラー: {e}")
            raise PaperFetchError(f"日付設定が無効です: {e}") from e
    
    def _is_paper_in_date_range(self, paper, start_date: datetime, end_date: datetime) -> bool:
        """論文が指定された日付範囲内にあるかチェック.
        
        Args:
            paper: arXiv論文オブジェクト
            start_date: 検索開始日（UTC）
            end_date: 検索終了日（UTC）
            
        Returns:
            日付範囲内の場合True、そうでなければFalse
        """
        try:
            # arXivの論文の投稿日を取得（UTC）
            paper_date = paper.published
            
            # タイムゾーンナイーブなdatetimeに変換（UTC想定）
            if paper_date.tzinfo is not None:
                paper_date = paper_date.replace(tzinfo=None)
            
            return start_date <= paper_date <= end_date
            
        except Exception as e:
            self.logger.warning(f"論文日付の解析に失敗: {e}")
            return False  # 日付が不明な場合は除外
    
    def _convert_arxiv_paper(self, paper, keyword: str) -> Dict:
        """arXiv論文オブジェクトを辞書形式に変換.
        
        Args:
            paper: arXiv論文オブジェクト
            keyword: この論文を見つけた検索キーワード
            
        Returns:
            論文データ辞書
        """
        # PDFリンクを安全に取得
        pdf_url = getattr(paper, 'pdf_url', None) or paper.entry_id.replace('/abs/', '/pdf/') + '.pdf'
        
        paper_dict = {
            'id': paper.entry_id,
            'title': paper.title.strip(),
            'authors': [str(author).strip() for author in paper.authors],
            'abstract': paper.summary.strip(),
            'published': paper.published.strftime('%Y-%m-%d'),
            'pdf_url': pdf_url,
            'categories': paper.categories,
            'keyword': keyword
        }
        
        # 重要度スコアを計算して追加
        importance_score = self._calculate_importance_score(paper, paper_dict)
        paper_dict['importance_score'] = importance_score
        
        # 関連度スコアを計算して追加（USER_KEYWORDSとの関連性）
        relevance_score = self._calculate_relevance_score(paper_dict, keyword)
        paper_dict['relevance_score'] = relevance_score
        
        return paper_dict
    
    def _calculate_importance_score(self, arxiv_paper, paper_dict: Dict) -> float:
        """論文の重要度スコアを計算.
        
        arXivでは引用数が取得できないため、以下の指標を組み合わせて評価：
        - 著者数（多著者論文は大規模研究の可能性）
        - タイトルの技術キーワード密度
        - アブストラクトの質的指標
        - カテゴリの重要度
        - 論文の新しさ vs 成熟度のバランス
        
        Args:
            arxiv_paper: arXiv論文オブジェクト
            paper_dict: 変換済み論文辞書
            
        Returns:
            重要度スコア（0-100の範囲）
        """
        score = 0.0
        
        # 1. 著者数による評価（5-15著者が最適、それ以上は減点）
        author_count = len(paper_dict.get('authors', []))
        if author_count >= 3:
            if author_count <= 8:
                score += 15  # 適度な共同研究
            elif author_count <= 15:
                score += 10  # 大規模研究
            else:
                score += 5   # 過度に大規模（質が薄い可能性）
        else:
            score += 5  # 少数著者研究
        
        # 2. タイトルの技術キーワード評価
        title = paper_dict.get('title', '').lower()
        title_score = self._evaluate_technical_keywords(title)
        score += title_score * 0.3  # 最大15点
        
        # 3. アブストラクトの質的評価
        abstract = paper_dict.get('abstract', '').lower()
        abstract_score = self._evaluate_abstract_quality(abstract)
        score += abstract_score * 0.2  # 最大10点
        
        # 4. カテゴリ重要度
        categories = paper_dict.get('categories', [])
        category_score = self._evaluate_category_importance(categories)
        score += category_score  # 最大20点
        
        # 5. 論文の年数による調整（新しすぎず古すぎない論文を優遇）
        age_score = self._evaluate_paper_age(paper_dict.get('published'))
        score += age_score  # 最大10点
        
        # 6. エネルギー・電力関連キーワードボーナス
        energy_bonus = self._evaluate_energy_keywords(title + ' ' + abstract)
        score += energy_bonus  # 最大30点
        
        # スコアを0-100の範囲に正規化
        normalized_score = min(100.0, max(0.0, score))
        
        self.logger.debug(
            f"論文重要度スコア計算: {paper_dict.get('title', '')[:50]}... = {normalized_score:.1f}"
        )
        
        return normalized_score
    
    def _evaluate_technical_keywords(self, text: str) -> float:
        """技術キーワードの密度を評価."""
        high_value_keywords = [
            'machine learning', 'deep learning', 'neural network', 'artificial intelligence',
            'optimization', 'algorithm', 'model', 'prediction', 'forecasting',
            'analysis', 'system', 'control', 'management', 'detection'
        ]
        
        score = 0
        words = text.split()
        total_words = len(words)
        
        for keyword in high_value_keywords:
            if keyword in text:
                # キーワードの重要度に応じて加点
                if keyword in ['machine learning', 'deep learning', 'neural network']:
                    score += 15
                elif keyword in ['optimization', 'prediction', 'forecasting']:
                    score += 10
                else:
                    score += 5
        
        # テキスト長に応じて正規化
        if total_words > 0:
            score = score * (min(20, total_words) / 20)
        
        return min(50.0, score)
    
    def _evaluate_abstract_quality(self, abstract: str) -> float:
        """アブストラクトの質を評価."""
        if not abstract or len(abstract) < 100:
            return 0.0
        
        score = 0
        
        # 長さによる評価
        length = len(abstract)
        if 200 <= length <= 2000:
            score += 20
        elif 100 <= length < 200:
            score += 10
        
        # 数値・統計データの存在
        if re.search(r'\d+\.?\d*%|\d+\.?\d*\s*(accuracy|precision|recall|f1)', abstract):
            score += 15  # 定量的結果を含む
        
        # 手法を示すキーワード
        methodology_keywords = ['propose', 'develop', 'introduce', 'present', 'implement']
        if any(keyword in abstract for keyword in methodology_keywords):
            score += 10
        
        return min(50.0, score)
    
    def _evaluate_category_importance(self, categories: List[str]) -> float:
        """arXivカテゴリの重要度を評価."""
        high_importance_categories = {
            'cs.AI': 20,      # Artificial Intelligence
            'cs.LG': 20,      # Machine Learning  
            'cs.SY': 15,      # Systems and Control
            'eess.SY': 15,    # Systems and Control (EESS)
            'cs.CV': 10,      # Computer Vision
            'cs.CL': 10,      # Computational Linguistics
            'stat.ML': 15,    # Machine Learning (Statistics)
            'math.OC': 10,    # Optimization and Control
            'physics.soc-ph': 8,  # Physics and Society
        }
        
        score = 0
        for category in categories:
            if category in high_importance_categories:
                score += high_importance_categories[category]
                break  # 最初にマッチしたカテゴリのみ評価
        
        return min(20.0, score)
    
    def _evaluate_paper_age(self, published_date: str) -> float:
        """論文の年数による評価."""
        try:
            pub_date = datetime.strptime(published_date, '%Y-%m-%d')
            days_old = (datetime.now() - pub_date).days
            
            # 最適な年数（6ヶ月〜2年）を優遇
            if 180 <= days_old <= 730:  # 6ヶ月〜2年
                return 10.0
            elif 90 <= days_old < 180:   # 3-6ヶ月
                return 8.0
            elif 730 < days_old <= 1460: # 2-4年
                return 6.0
            elif days_old < 90:          # 3ヶ月未満（新しすぎる）
                return 4.0
            else:                        # 4年以上（古い）
                return 2.0
                
        except (ValueError, TypeError):
            return 5.0  # デフォルト値
    
    def _evaluate_energy_keywords(self, text: str) -> float:
        """エネルギー・電力関連キーワードの評価."""
        energy_keywords = {
            # 高価値キーワード（30点）
            'renewable energy': 30, 'smart grid': 30, 'energy storage': 30,
            'demand response': 25, 'microgrid': 25, 'power system': 25,
            # 中価値キーワード（15-20点）  
            'solar power': 20, 'wind power': 20, 'energy management': 20,
            'load forecasting': 18, 'power forecasting': 18,
            'energy efficiency': 15, 'grid stability': 15,
            # 基本キーワード（10点）
            'electricity': 10, 'power': 8, 'energy': 5
        }
        
        max_score = 0
        for keyword, points in energy_keywords.items():
            if keyword in text:
                max_score = max(max_score, points)
        
        return max_score
    
    def _calculate_relevance_score(self, paper_dict: Dict, search_keyword: str) -> float:
        """論文のUSER_KEYWORDSとの関連度を計算.
        
        Args:
            paper_dict: 論文データ辞書
            search_keyword: この論文を発見した検索キーワード
            
        Returns:
            関連度スコア（0-100の範囲）
        """
        if not hasattr(self.config, 'USER_KEYWORDS') or not self.config.USER_KEYWORDS:
            return 50.0  # USER_KEYWORDSが設定されていない場合はデフォルト値
        
        title = paper_dict.get('title', '').lower()
        abstract = paper_dict.get('abstract', '').lower()
        categories = paper_dict.get('categories', [])
        
        relevance_score = 0.0
        
        # 1. タイトルでのキーワードマッチ（高重要度）
        title_score = self._calculate_keyword_match_score(title, self.config.USER_KEYWORDS, weight=3.0)
        relevance_score += title_score
        
        # 2. アブストラクトでのキーワードマッチ（中重要度）
        abstract_score = self._calculate_keyword_match_score(abstract, self.config.USER_KEYWORDS, weight=2.0)
        relevance_score += abstract_score
        
        # 3. 検索キーワードとUSER_KEYWORDSの関連性
        search_keyword_score = self._calculate_keyword_match_score(search_keyword.lower(), self.config.USER_KEYWORDS, weight=1.5)
        relevance_score += search_keyword_score
        
        # 4. 関連語・同義語によるマッチング
        semantic_score = self._calculate_semantic_relevance(title + ' ' + abstract, self.config.USER_KEYWORDS)
        relevance_score += semantic_score
        
        # 5. カテゴリベースの関連性
        category_score = self._calculate_category_relevance(categories)
        relevance_score += category_score
        
        # 6. 共起キーワードによる関連性強化
        cooccurrence_score = self._calculate_cooccurrence_score(title + ' ' + abstract)
        relevance_score += cooccurrence_score
        
        # スコアを0-100の範囲に正規化
        normalized_score = min(100.0, max(0.0, relevance_score))
        
        self.logger.debug(
            f"関連度スコア計算: {paper_dict.get('title', '')[:40]}... = {normalized_score:.1f}"
        )
        
        return normalized_score
    
    def _calculate_keyword_match_score(self, text: str, keywords: List[str], weight: float = 1.0) -> float:
        """テキスト内でのキーワードマッチスコアを計算."""
        if not text or not keywords:
            return 0.0
        
        score = 0.0
        text_words = text.split()
        text_length = len(text_words)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # 完全一致（高得点）
            if keyword_lower in text:
                score += 20.0 * weight
                
                # 近接性ボーナス（キーワードが近くにある場合）
                words = text.split()
                keyword_words = keyword_lower.split()
                if len(keyword_words) > 1:
                    # 複数語キーワードの場合、語順も考慮
                    score += 5.0 * weight
                
            # 部分一致（中得点）
            else:
                keyword_words = keyword_lower.split()
                matched_words = sum(1 for word in keyword_words if word in text)
                if matched_words > 0:
                    partial_score = (matched_words / len(keyword_words)) * 10.0 * weight
                    score += partial_score
        
        # テキスト長に応じた正規化
        if text_length > 0:
            score = score * (min(100, text_length) / 100)
        
        return min(50.0 * weight, score)
    
    def _calculate_semantic_relevance(self, text: str, user_keywords: List[str]) -> float:
        """関連語・同義語による意味的関連性を計算."""
        # 関連語辞書（ドメイン特化）
        semantic_relations = {
            'prediction': ['forecasting', 'estimation', 'modeling', 'analysis', 'algorithm'],
            'energy': ['power', 'electricity', 'renewable', 'solar', 'wind', 'storage'],
            'machine learning': ['deep learning', 'neural network', 'ai', 'algorithm', 'model'],
            'optimization': ['control', 'management', 'efficiency', 'scheduling', 'planning'],
            'smart grid': ['microgrid', 'grid', 'distribution', 'transmission', 'demand response'],
            'demand response': ['load balancing', 'demand management', 'peak shaving', 'flexibility']
        }
        
        score = 0.0
        text_lower = text.lower()
        
        for keyword in user_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in semantic_relations:
                related_words = semantic_relations[keyword_lower]
                matches = sum(1 for word in related_words if word in text_lower)
                if matches > 0:
                    score += (matches / len(related_words)) * 15.0
        
        return min(20.0, score)
    
    def _calculate_category_relevance(self, categories: List[str]) -> float:
        """arXivカテゴリとUSER_KEYWORDSの関連性を計算."""
        # カテゴリとキーワードの関連性マッピング
        category_keyword_mapping = {
            'cs.AI': ['prediction', 'machine learning', 'optimization'],
            'cs.LG': ['prediction', 'machine learning'],
            'cs.SY': ['optimization', 'smart grid', 'demand response'],
            'eess.SY': ['optimization', 'smart grid', 'energy'],
            'physics.app-ph': ['energy'],
            'cond-mat.stat-mech': ['energy', 'optimization']
        }
        
        if not hasattr(self.config, 'USER_KEYWORDS'):
            return 0.0
        
        score = 0.0
        for category in categories:
            if category in category_keyword_mapping:
                relevant_keywords = category_keyword_mapping[category]
                user_keywords_lower = [kw.lower() for kw in self.config.USER_KEYWORDS]
                
                matches = sum(1 for kw in relevant_keywords 
                            if any(kw in user_kw for user_kw in user_keywords_lower))
                if matches > 0:
                    score += matches * 5.0
        
        return min(15.0, score)
    
    def _calculate_cooccurrence_score(self, text: str) -> float:
        """キーワード共起による関連性を計算."""
        if not hasattr(self.config, 'USER_KEYWORDS'):
            return 0.0
        
        text_lower = text.lower()
        user_keywords_lower = [kw.lower() for kw in self.config.USER_KEYWORDS]
        
        # 複数のUSER_KEYWORDSが同じテキストに出現する場合にボーナス
        present_keywords = sum(1 for kw in user_keywords_lower if kw in text_lower)
        
        if present_keywords >= 2:
            # 共起ボーナス: n個のキーワードがある場合 n*(n-1) のボーナス
            cooccurrence_bonus = present_keywords * (present_keywords - 1) * 3.0
            return min(15.0, cooccurrence_bonus)
        
        return 0.0
    
    def _get_recency_score(self, published_date: str) -> float:
        """論文の新しさをスコア化（0-100）."""
        try:
            pub_date = datetime.strptime(published_date, '%Y-%m-%d')
            days_old = (datetime.now() - pub_date).days
            
            # 新しい論文ほど高いスコア（最大100点）
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
            return 50.0  # デフォルト値
    
    def _filter_recent_papers(self, papers: List[Dict]) -> List[Dict]:
        """設定された日付範囲内の論文のみにフィルタリング.
        
        Args:
            papers: 論文辞書のリスト
            
        Returns:
            フィルタリングされた論文のリスト
        """
        try:
            start_date, end_date = self.config.get_date_range()
            recent_papers = []
            
            for paper in papers:
                try:
                    published_date = datetime.strptime(paper['published'], '%Y-%m-%d')
                    if start_date <= published_date <= end_date:
                        recent_papers.append(paper)
                except (ValueError, KeyError) as e:
                    self.logger.warning(
                        f"論文{paper.get('id', 'unknown')}の日付形式が無効です: {e}"
                    )
                    continue
                
            return recent_papers
            
        except ValueError as e:
            self.logger.error(f"日付範囲設定エラー: {e}")
            # エラー時は元のリストをそのまま返す
            return papers
    
    def _remove_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """論文IDに基づく重複論文の除去.
        
        Args:
            papers: 論文辞書のリスト
            
        Returns:
            重複が除去されたリスト
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
    """論文取得エラー用のカスタム例外."""
    pass