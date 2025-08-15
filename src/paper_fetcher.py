import arxiv
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import logging

class PaperFetcher:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def fetch_arxiv_papers(self, keywords: List[str], max_results: int = 10) -> List[Dict]:
        """arXivから論文を取得"""
        papers = []
        
        for keyword in keywords:
            try:
                # 検索クエリ作成（電力・AI・IoT関連カテゴリ）
                query = f'({keyword}) AND (cat:cs.AI OR cat:cs.LG OR cat:eess.SP OR cat:eess.SY OR cat:cs.DC)'
                
                search = arxiv.Search(
                    query=query,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending
                )
                
                for paper in search.results():
                    # 投稿日フィルタ
                    if self._is_recent_paper(paper.published):
                        paper_data = {
                            'id': paper.entry_id,
                            'title': paper.title,
                            'authors': [str(author) for author in paper.authors],
                            'abstract': paper.summary,
                            'published': paper.published.strftime('%Y-%m-%d'),
                            'pdf_url': paper.pdf_url,
                            'categories': paper.categories,
                            'keyword': keyword.strip()
                        }
                        papers.append(paper_data)
                        
            except Exception as e:
                self.logger.error(f"arXiv検索エラー (keyword: {keyword}): {e}")
        
        # 重複除去
        unique_papers = self._remove_duplicates(papers)
        self.logger.info(f"取得論文数: {len(unique_papers)}")
        
        return unique_papers[:max_results]
    
    def _is_recent_paper(self, published_date) -> bool:
        """指定日数内の論文かチェック"""
        cutoff_date = datetime.now() - timedelta(days=self.config.DAYS_BACK)
        return published_date.replace(tzinfo=None) >= cutoff_date
    
    def _remove_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """重複論文を除去"""
        seen_ids = set()
        unique_papers = []
        
        for paper in papers:
            if paper['id'] not in seen_ids:
                seen_ids.add(paper['id'])
                unique_papers.append(paper)
        
        return unique_papers