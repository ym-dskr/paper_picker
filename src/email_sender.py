import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict
import logging

class EmailSender:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_summary_email(self, papers: List[Dict]) -> bool:
        """要約論文をメール送信"""
        try:
            # メール本文作成
            email_body = self._create_email_body(papers)
            subject = f"📚 研究論文要約レポート - {datetime.now().strftime('%Y年%m月%d日')}"
            
            # メール送信
            success = self._send_email(subject, email_body)
            
            if success:
                self.logger.info(f"メール送信成功: {len(papers)}件の論文")
            else:
                self.logger.error("メール送信失敗")
            
            return success
            
        except Exception as e:
            self.logger.error(f"メール送信エラー: {e}")
            return False
    
    def _create_email_body(self, papers: List[Dict]) -> str:
        """メール本文作成"""
        if not papers:
            return "本日は新しい論文が見つかりませんでした。"
        
        # 重要度別に分類
        high_priority = [p for p in papers if '★★★★★' in p.get('summary_ja', '') or '★★★★☆' in p.get('summary_ja', '')]
        medium_priority = [p for p in papers if p not in high_priority]
        
        email_body = f"""
# 🔬 電力・AI・IoT分野 研究論文要約レポート

**配信日時**: {datetime.now().strftime('%Y年%m月%d日 %H時%M分')}  
**取得論文数**: {len(papers)}件  
**高優先度論文**: {len(high_priority)}件  

---

## 📌 本日のハイライト

"""
        
        # 高優先度論文
        if high_priority:
            email_body += "### 🌟 注目論文\n\n"
            for paper in high_priority:
                email_body += paper.get('summary_ja', 'No summary') + "\n\n"
        
        # その他の論文
        if medium_priority:
            email_body += "### 📋 その他の論文\n\n"
            for paper in medium_priority:
                email_body += paper.get('summary_ja', 'No summary') + "\n\n"
        
        email_body += f"""
---

## 📊 統計情報

- **検索キーワード**: {', '.join(self.config.SEARCH_KEYWORDS)}
- **検索期間**: 過去{self.config.DAYS_BACK}日間
- **データソース**: arXiv.org
- **システム**: Raspberry Pi 自動論文要約システム

---

*このメールは自動生成されています。配信停止をご希望の場合はお知らせください。*
"""
        
        return email_body
    
    def _send_email(self, subject: str, body: str) -> bool:
        """実際のメール送信処理"""
        try:
            # MIMEオブジェクト作成
            msg = MIMEMultipart()
            msg['From'] = self.config.SENDER_EMAIL
            msg['To'] = ', '.join(self.config.RECIPIENT_EMAILS)
            msg['Subject'] = subject
            
            # 本文添付（HTML形式）
            html_body = body.replace('\n', '<br>')  # 改行をHTMLに変換
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # SMTP接続・送信
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.SENDER_EMAIL, self.config.SENDER_PASSWORD)
                
                for recipient in self.config.RECIPIENT_EMAILS:
                    if recipient.strip():  # 空文字チェック
                        server.send_message(msg, to_addrs=[recipient.strip()])
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP送信エラー: {e}")
            return False