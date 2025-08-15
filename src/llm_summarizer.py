import openai
from typing import Dict
import logging
import time

class LLMSummarizer:
    def __init__(self, config):
        self.config = config
        openai.api_key = config.OPENAI_API_KEY
        self.logger = logging.getLogger(__name__)
    
    def summarize_paper(self, paper: Dict) -> Dict:
        """論文をLLMで要約"""
        try:
            prompt = self._create_summary_prompt(paper)
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは電力・AI・IoT分野の専門研究者です。論文を日本語で分かりやすく要約してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            paper_with_summary = paper.copy()
            paper_with_summary['summary_ja'] = summary
            paper_with_summary['summary_generated'] = True
            
            # API制限対策（1秒待機）
            time.sleep(1)
            
            return paper_with_summary
            
        except Exception as e:
            self.logger.error(f"要約生成エラー (paper: {paper['title'][:50]}...): {e}")
            paper['summary_ja'] = "要約生成に失敗しました"
            paper['summary_generated'] = False
            return paper
    
    def _create_summary_prompt(self, paper: Dict) -> str:
        """要約生成用プロンプト作成"""
        authors_str = ', '.join(paper['authors'][:3])  # 最初の3名のみ
        if len(paper['authors']) > 3:
            authors_str += ' ほか'
        
        prompt = f"""
以下の研究論文について、日本語で詳細な要約と解説を作成してください。

【論文情報】
タイトル: {paper['title']}
著者: {authors_str}
投稿日: {paper['published']}
分野: {', '.join(paper['categories'])}

【アブストラクト】
{paper['abstract']}

【出力形式】
## 📄 {paper['title']}

**著者**: {authors_str}  
**投稿日**: {paper['published']}  
**分野**: {', '.join(paper['categories'])}

### 🎯 研究の背景・目的
[この研究が解決しようとしている課題や背景]

### 🔬 提案手法
[論文で提案されている具体的な手法やアプローチ]

### 📊 主な成果・結果
[実験結果や主な発見事項]

### 💡 実用化の可能性
[電力・AI・IoT分野での実用化可能性や応用例]

### ⭐ 重要度 (5段階評価)
★★★☆☆ [評価の理由も含めて記載]

---
"""
        return prompt