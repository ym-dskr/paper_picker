"""LLMベースの論文要約機能

このモジュールは、適切なエラーハンドリングとレート制限を含む
OpenAIの言語モデルを使用した研究論文の日本語要約生成を処理します。
"""

import openai
import time
from typing import Dict, Optional
import logging


class LLMSummarizer:
    """OpenAI LLMを使用して研究論文の日本語要約を生成するクラス
    
    このクラスは、OpenAIのAPIとの相互作用を管理し、適切な
    エラーハンドリング、レート制限、プロンプト管理を含む
    研究論文の構造化された日本語要約を生成します。
    
    属性:
        config: API設定を含む設定オブジェクト
        logger (logging.Logger): このクラス用のロガーインスタンス
    """
    
    def __init__(self, config) -> None:
        """LLM要約クラスの初期化
        
        引数:
            config: OpenAI APIキーと設定を含む設定オブジェクト
            
        例外:
            ValueError: OpenAI APIキーが提供されていない場合
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        if not config.OPENAI_API_KEY:
            raise ValueError("要約処理にはOpenAI APIキーが必要です")
            
        openai.api_key = config.OPENAI_API_KEY
    
    def summarize_paper(self, paper: Dict) -> Dict:
        """研究論文の日本語要約を生成
        
        引数:
            paper (Dict): タイトル、アブストラクト、著者等を含む論文辞書
            
        戻り値:
            Dict: 日本語要約が追加された更新された論文辞書
            
        例外:
            SummarizationError: 要約生成が失敗した場合
        """
        if not self._validate_paper_data(paper):
            self.logger.warning(f"要約処理用の無効な論文データ: {paper.get('id', 'unknown')}")
            paper['summary_ja'] = "要約生成に失敗しました（データ不備）"
            paper['summary_generated'] = False
            return paper
        
        # 電力関連度をチェック（事前に評価済みの場合はそれを使用）
        power_relevance = paper.get('power_relevance_score')
        if power_relevance is None:
            power_relevance = self._assess_power_relevance(paper)
        
        if power_relevance < 0.3:  # 関連度が低い場合は要約をスキップ
            self.logger.info(f"電力関連度が低いためスキップ: {paper.get('title', '')[:50]}")
            paper['summary_ja'] = "電力分野への関連度が低いため要約対象外"
            paper['summary_generated'] = False
            paper['power_relevance'] = power_relevance
            return paper
        
        try:
            prompt = self._create_summary_prompt(paper)
            summary = self._generate_summary_with_retry(prompt, max_retries=3)
            
            paper_with_summary = paper.copy()
            paper_with_summary['summary_ja'] = summary
            paper_with_summary['summary_generated'] = True
            paper_with_summary['power_relevance'] = power_relevance
            
            # APIレート制限回避のための待機
            time.sleep(1)
            
            self.logger.info(f"論文の要約生成が成功しました: {paper['id']}")
            return paper_with_summary
            
        except Exception as e:
            self.logger.error(f"論文'{paper.get('title', '')[:50]}...'の要約生成に失敗しました: {e}")
            paper['summary_ja'] = "要約生成に失敗しました"
            paper['summary_generated'] = False
            paper['power_relevance'] = power_relevance
            return paper
    
    def _generate_summary_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """API失敗時のリトライロジック付き要約生成
        
        引数:
            prompt (str): LLMに送信するプロンプト
            max_retries (int): 最大リトライ回数
            
        戻り値:
            str: 生成された要約テキスト
            
        例外:
            SummarizationError: 全てのリトライ試行が失敗した場合
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    # model="gpt-3.5-turbo",
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
                            してください。 
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
                self.logger.warning(f"要約生成試行{attempt + 1}回目が失敗しました: {e}")
                
                if attempt < max_retries - 1:
                    # 指数バックオフ
                    wait_time = 2 ** attempt
                    self.logger.info(f"{wait_time}秒後にリトライします...")
                    time.sleep(wait_time)
                    
        raise SummarizationError(f"{max_retries}回の試行後に要約生成に失敗しました") from last_exception
    
    def _create_summary_prompt(self, paper: Dict) -> str:
        """論文要約用の構造化プロンプトを作成
        
        引数:
            paper (Dict): 論文データ辞書
            
        戻り値:
            str: LLM用にフォーマットされたプロンプト
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
        
        prompt = f"""以下の研究論文について、電力分野の観点から日本語で詳細な要約と解説を作成してください。

【論文情報】
タイトル: {paper.get('title', 'N/A')}
著者: {authors_str}
投稿日: {paper.get('published', 'N/A')}
分野: {categories_str}
PDF: {paper.get('pdf_url', 'N/A')}

【アブストラクト】
{abstract}

【出力形式】
📄 {paper.get('title', 'N/A')}
📎 PDF: {paper.get('pdf_url', 'N/A')}

著者: {authors_str}  
投稿日: {paper.get('published', 'N/A')}  
分野: {categories_str}

🎯 研究の背景・目的
[この研究が解決しようとしている電力・エネルギー分野の課題や背景]

🔬 提案手法
[論文で提案されている具体的な手法やアプローチ、使用されているAI技術]

📊 主な成果・結果
[実験結果や主な発見事項、予測精度や性能向上]

💡 電力分野への応用
[電力需要予測、再エネ発電量予測、グリッド運用への具体的応用可能性]

⭐ 電力分野重要度 (5段階評価)
★★★☆☆ [電力業界での実用性と革新性の観点から評価理由を記載]

🔍 注目ポイント
[以下の重要技術領域における注目点を整理]
- 電力需要予測技術: [該当する場合の技術的特徴]
- 再エネ発電量予測技術: [太陽光・風力予測への応用可能性]
- AI/生成AI技術: [使用されているAI手法の特徴と革新性]
- グリッド分散化技術: [分散エネルギー資源管理への貢献]
- 電力価格予測技術: [電力市場への影響と予測手法]
- その他重要技術: [上記以外の電力分野への重要な貢献]

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
    
    def _assess_power_relevance(self, paper: Dict) -> float:
        """論文のAI・予測・IoT×電力分野関連度を評価
        
        4段階のキーワードカテゴリで関連度を評価：
        - 最高関連度（0.4）: AI×予測×電力の融合技術
        - 高関連度（0.3）: 電力予測・IoT特化技術  
        - 中関連度（0.2）: AI・予測技術一般
        - IoT基盤（0.15）: IoT・技術基盤
        
        引数:
            paper (Dict): 論文データ辞書
            
        戻り値:
            float: 関連度スコア（0.0-1.0）
        """
        title = paper.get('title', '').lower()
        abstract = paper.get('abstract', '').lower()
        text = f"{title} {abstract}"
        
        # 最高関連度キーワード（重み0.4）- AI×予測×電力の融合技術
        ultra_high_keywords = [
            'ai power forecast', 'machine learning energy prediction', 'deep learning power forecast',
            'neural network demand forecast', 'ai renewable energy forecast', 'smart grid ai',
            'generative ai energy', 'transformer power prediction', 'lstm energy forecast',
            'reinforcement learning grid', 'iot energy management', 'edge computing power',
            'digital twin energy', 'ai microgrid', 'federated learning energy'
        ]
        
        # 高関連度キーワード（重み0.3）- 電力予測・IoT特化
        high_priority_keywords = [
            'power forecast', 'demand forecast', 'energy forecast', 'wind power forecast',
            'solar forecast', 'photovoltaic forecast', 'renewable energy forecast',
            'load forecast', 'grid forecast', 'electricity demand forecast',
            'iot power monitoring', 'smart meter', 'energy iot', 'power iot',
            'edge ai energy', 'real-time power prediction', 'time series energy'
        ]
        
        # 中関連度キーワード（重み0.2）- AI・予測技術
        medium_priority_keywords = [
            'machine learning', 'deep learning', 'neural network', 'artificial intelligence',
            'prediction model', 'forecasting model', 'time series prediction',
            'lstm', 'transformer', 'cnn', 'reinforcement learning', 'generative ai',
            'anomaly detection', 'pattern recognition', 'optimization algorithm',
            'data mining', 'predictive analytics', 'computer vision'
        ]
        
        # IoT・技術基盤キーワード（重み0.15）
        iot_tech_keywords = [
            'internet of things', 'iot', 'edge computing', 'fog computing',
            'wireless sensor', 'sensor network', 'smart sensor', 'embedded system',
            'real-time monitoring', 'data acquisition', 'cloud computing',
            'distributed computing', 'cyber-physical system', 'digital twin',
            'blockchain energy', 'federated learning', 'edge ai'
        ]
        
        score = 0.0
        
        # 最高関連度キーワードのチェック（AI×予測×電力融合）
        for keyword in ultra_high_keywords:
            if keyword in text:
                score += 0.4
        
        # 高関連度キーワードのチェック（電力予測・IoT特化）
        for keyword in high_priority_keywords:
            if keyword in text:
                score += 0.3
        
        # 中関連度キーワードのチェック（AI・予測技術）
        for keyword in medium_priority_keywords:
            if keyword in text:
                score += 0.2
        
        # IoT・技術基盤キーワードのチェック
        for keyword in iot_tech_keywords:
            if keyword in text:
                score += 0.15
        
        # スコアを0-1の範囲に正規化
        return min(1.0, score)
    
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
        
        summarized_papers = []
        success_count = 0
        
        for i, paper in enumerate(papers, 1):
            self.logger.info(f"論文要約中 {i}/{len(papers)}: {paper.get('title', '')[:50]}...")
            
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
    """要約関連エラー用のカスタム例外"""
    pass