"""LLMベースの論文要約機能モジュール.

このモジュールは適切なエラーハンドリングとレート制限を含む
OpenAIの言語モデルを使用した研究論文の日本語要約生成を処理します。
"""

import openai
import time
from typing import Dict, Optional
import logging


class LLMSummarizer:
    """OpenAI LLMを使用して研究論文の日本語要約を生成するクラス.
    
    このクラスはOpenAIのAPIとの相互作用を管理し、適切な
    エラーハンドリング、レート制限、プロンプト管理を含む
    研究論文の構造化された日本語要約を生成します。
    
    Attributes:
        config: API設定を含む設定オブジェクト
        logger: このクラス用のロガーインスタンス
    """
    
    def __init__(self, config) -> None:
        """LLM要約クラスの初期化.
        
        Args:
            config: OpenAI APIキーと設定を含む設定オブジェクト
            
        Raises:
            ValueError: OpenAI APIキーが提供されていない場合
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if not config.OPENAI_API_KEY:
            raise ValueError("要約処理にはOpenAI APIキーが必要です")
            
        openai.api_key = config.OPENAI_API_KEY
    
    def summarize_paper(self, paper: Dict) -> Dict:
        """研究論文の日本語要約を生成.
        
        Args:
            paper: タイトル、アブストラクト、著者等を含む論文辞書
            
        Returns:
            日本語要約が追加された更新された論文辞書
            
        Raises:
            SummarizationError: 要約生成が失敗した場合
        """
        if not self._validate_paper_data(paper):
            self.logger.warning(
                f"要約処理用の無効な論文データ: {paper.get('id', 'unknown')}"
            )
            paper['summary_ja'] = "要約生成に失敗しました（データ不備）"
            paper['summary_generated'] = False
            return paper
        
        # キーワード関連度をチェック
        is_relevant = self._assess_keyword_relevance(paper, self.config.USER_KEYWORDS)
        
        if not is_relevant:  # キーワードにマッチしない場合は要約をスキップ
            self.logger.info(
                f"設定キーワードに関連しないためスキップ: "
                f"{paper.get('title', '')[:50]}"
            )
            paper['summary_ja'] = "設定されたキーワードに関連しないため要約対象外"
            paper['summary_generated'] = False
            paper['keyword_relevance'] = False
            return paper
        
        try:
            prompt = self._create_summary_prompt(paper)
            summary = self._generate_summary_with_retry(prompt, max_retries=3)
            
            paper_with_summary = paper.copy()
            paper_with_summary['summary_ja'] = summary
            paper_with_summary['summary_generated'] = True
            paper_with_summary['keyword_relevance'] = True
            
            # APIレート制限回避のための待機
            time.sleep(1)
            
            self.logger.info(f"論文の要約生成が成功しました: {paper['id']}")
            return paper_with_summary
            
        except Exception as e:
            self.logger.error(
                f"論文'{paper.get('title', '')[:50]}...'の要約生成に失敗しました: {e}"
            )
            paper['summary_ja'] = "要約生成に失敗しました"
            paper['summary_generated'] = False
            paper['keyword_relevance'] = is_relevant
            return paper
    
    def _generate_summary_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """API失敗時のリトライロジック付き要約生成.
        
        Args:
            prompt: LLMに送信するプロンプト
            max_retries: 最大リトライ回数
            
        Returns:
            生成された要約テキスト
            
        Raises:
            SummarizationError: 全てのリトライ試行が失敗した場合
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content":
                            """
                            あなたは電力システム・エネルギー予測・AI技術の専門研究者です。
                            電力需要予測、再生可能エネルギー発電量予測、スマートグリッド、
                            AI/生成AI技術の観点から論文を日本語で分かりやすく要約してください。
                            初心者にもわかりやすいよう、難解な単語が出た場合は補足や解説も付与
                            しつつ説明してください。
                            
                            重要: PDFリンクは提供されたURLをそのまま正確に記載し、
                            リンクを変更・短縮・修正しないでください。
                            """
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.3,
                    timeout=30
                )
                
                summary = response.choices[0].message.content
                if not summary or len(summary.strip()) < 50:
                    raise SummarizationError("生成された要約が短すぎるか空です")
                    
                return summary.strip()
                
            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"要約生成試行{attempt + 1}回目が失敗しました: {e}"
                )
                
                if attempt < max_retries - 1:
                    # 指数バックオフ
                    wait_time = 2 ** attempt
                    self.logger.info(f"{wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                    
        raise SummarizationError(
            f"{max_retries}回の試行後に要約生成に失敗しました"
        ) from last_exception
    
    def _create_summary_prompt(self, paper: Dict) -> str:
        """論文要約用の構造化プロンプトを作成.
        
        Args:
            paper: 論文データ辞書
            
        Returns:
            LLM用にフォーマットされたプロンプト
        """
        # 可読性のため著者を最初の3名に制限
        authors = paper.get('authors', [])
        authors_str = ', '.join(authors[:3])
        if len(authors) > 3:
            authors_str += ' ほか'
        
        # 長すぎる場合はアブストラクトを切り詰め
        abstract = paper.get('abstract', '')
        if len(abstract) > 2000:
            abstract = abstract[:2000] + "..."
        
        categories_str = ', '.join(paper.get('categories', []))
        
        pdf_url = paper.get('pdf_url', 'N/A')
        importance_score = paper.get('importance_score', 0)
        
        # 重要度に応じてプロンプトを調整
        detail_instruction = ""
        if importance_score >= 80:
            detail_instruction = "【高重要度論文】この論文は特に重要と評価されています。より詳細で具体的な要約を作成してください。"
        elif importance_score >= 60:
            detail_instruction = "【中重要度論文】この論文は重要と評価されています。技術的な詳細に注目して要約してください。"
        
        prompt = f"""以下の研究論文について、電力分野の観点から日本語で詳細な要約と解説を作成してください。
{detail_instruction}

【論文情報】
タイトル: {paper.get('title', 'N/A')}
著者: {authors_str}
投稿日: {paper.get('published', 'N/A')}
分野: {categories_str}
重要度スコア: {importance_score:.1f}/100
PDF: {pdf_url}

【アブストラクト】
{abstract}

【重要な指示】
出力時は以下のPDFリンクをそのまま正確に記載してください: {pdf_url}

【出力形式】
📄 {paper.get('title', 'N/A')}
📎 PDF: {pdf_url}

著者: {authors_str}  
投稿日: {paper.get('published', 'N/A')}  
分野: {categories_str}

🎯 研究の背景・目的
[この研究が解決しようとしている電力・エネルギー分野の課題や背景]

🔬 提案手法
[論文で提案されている具体的な手法やアプローチ、使用されているAI技術をなるべく具体的かつ簡潔に]

📊 主な成果・結果
[実験結果や主な発見事項、予測精度や性能向上]

💡 電力分野への応用
[電力需要予測、再エネ発電量予測、グリッド運用への具体的応用可能性]

⭐ 電力分野重要度 (5段階評価)
★★★☆☆ [電力業界での実用性と革新性の観点から評価理由を記載]

---
"""
        return prompt
    
    def _validate_paper_data(self, paper: Dict) -> bool:
        """要約前の論文データのバリデーション
        
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
        
        # タイトルが意味のあるものかチェック（空白のみでなく短すぎない）
        title = paper.get('title', '').strip()
        if len(title) < 10:
            self.logger.warning(f"論文タイトルが短すぎます: '{title}'")
            return False
            
        return True
    
    def _assess_keyword_relevance(self, paper: Dict, keywords: list[str]) -> bool:
        """論文がユーザー設定キーワードのいずれかに関連するかを評価
        
        引数:
            paper (Dict): 論文データ辞書
            keywords (list[str]): ユーザー設定キーワードのリスト
            
        戻り値:
            bool: いずれかのキーワードにマッチした場合はTrue
        """
        if not keywords:
            return True  # キーワードが設定されていない場合は全て要約対象
            
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        text = f"{title} {abstract}"
        
        # いずれかのキーワードが部分一致するかチェック
        for keyword in keywords:
            if keyword.lower() in text:
                return True
                
        return False
    
    def batch_summarize(self, papers: list[Dict]) -> list[Dict]:
        """進捗追跡付きの複数論文の要約処理
        
        引数:
            papers (list[Dict]): 論文辞書のリスト
            
        戻り値:
            list[Dict]: 要約が追加された論文のリスト
        """
        if not papers:
            self.logger.warning("バッチ要約処理用の論文が提供されていません")
            return []
        
        # 重要度順にソートしてから処理
        sorted_papers = sorted(
            papers, 
            key=lambda x: x.get('importance_score', 0), 
            reverse=True
        )
        
        summarized_papers = []
        success_count = 0
        
        for i, paper in enumerate(sorted_papers, 1):
            importance = paper.get('importance_score', 0)
            relevance = paper.get('relevance_score', 0)
            self.logger.info(
                f"論文要約中 {i}/{len(papers)} (重要度:{importance:.1f}, 関連度:{relevance:.1f}): "
                f"{paper.get('title', '')[:50]}..."
            )
            
            try:
                summarized_paper = self.summarize_paper(paper)
                summarized_papers.append(summarized_paper)
                
                if summarized_paper.get('summary_generated', False):
                    success_count += 1
                    
            except Exception as e:
                self.logger.error(f"論文{i}の要約に失敗しました: {e}")
                paper['summary_ja'] = "要約生成に失敗しました"
                paper['summary_generated'] = False
                summarized_papers.append(paper)
        
        self.logger.info(f"バッチ要約処理が完了しました: {success_count}/{len(papers)}件成功")
        return summarized_papers


class SummarizationError(Exception):
    """要約関連エラー用のカスタム例外."""
    pass