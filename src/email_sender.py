"""研究論文要約メール送信機能

このモジュールは、適切なGmail表示フォーマットとエラーハンドリングを含む
研究論文要約を含むメール通知の作成と送信を処理します。
"""

import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional
import logging


class EmailSender:
    """研究論文要約のメール通知を管理するクラス
    
    このクラスは、論文要約と完全な論文リストを含むメールレポートの
    フォーマットと送信を処理し、Gmail表示に最適化され、適切な
    エラーハンドリングとSMTP設定を含みます。
    
    属性:
        config: メール設定を含む設定オブジェクト
        logger (logging.Logger): このクラス用のロガーインスタンス
    """
    
    def __init__(self, config) -> None:
        """メール送信クラスの初期化
        
        引数:
            config: メール設定を含む設定オブジェクト
            
        例外:
            ValueError: 必要なメール設定が不足している場合
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # メール設定のバリデーション
        self._validate_email_config()
    
    def send_summary_email(
        self, 
        papers: List[Dict], 
        all_papers: Optional[List[Dict]] = None
    ) -> bool:
        """論文要約と完全な論文リストを含むメールを送信
        
        引数:
            papers (List[Dict]): 要約済み論文のリスト
            all_papers (Optional[List[Dict]]): 発見された全論文のリスト
            
        戻り値:
            bool: メールが正常に送信された場合はTrue、そうでなければFalse
        """
        try:
            email_body = self._create_email_body(papers, all_papers)
            subject = self._create_subject()
            
            success = self._send_email(subject, email_body)
            
            if success:
                self.logger.info(f"メール送信成功: {len(papers)}件の要約済み論文")
            else:
                self.logger.error("メール送信失敗")
            
            return success
            
        except Exception as e:
            self.logger.error(f"メール送信エラー: {e}")
            return False
    
    def _create_subject(self) -> str:
        """メール件名の作成
        
        戻り値:
            str: フォーマットされたメール件名
        """
        return f"📚 研究論文要約レポート - {datetime.now().strftime('%Y年%m月%d日')}"
    
    def _create_email_body(
        self, 
        papers: List[Dict], 
        all_papers: Optional[List[Dict]] = None
    ) -> str:
        """論文要約と完全リストを含むメール本文の作成
        
        引数:
            papers (List[Dict]): 要約済み論文のリスト
            all_papers (Optional[List[Dict]]): 発見された全論文のリスト
            
        戻り値:
            str: フォーマットされたメール本文
        """
        if not papers:
            return "本日は新しい論文が見つかりませんでした。"
        
        if all_papers is None:
            all_papers = papers
        
        # メールセクションの構築
        header = self._create_header(papers, all_papers)
        summary_section = self._create_summary_section(papers)
        paper_list_section = self._create_paper_list_section(all_papers, papers)
        footer = self._create_footer()
        
        return f"{header}\\n{summary_section}\\n{paper_list_section}\\n{footer}"
    
    def _create_header(self, papers: List[Dict], all_papers: List[Dict]) -> str:
        """メールヘッダーセクションの作成
        
        引数:
            papers (List[Dict]): 要約済み論文
            all_papers (List[Dict]): 発見された全論文
            
        戻り値:
            str: ヘッダーセクション
        """
        high_priority = self._count_high_priority_papers(papers)
        
        return f"""🔬 電力・AI・IoT分野 研究論文要約レポート

配信日時: {datetime.now().strftime('%Y年%m月%d日 %H時%M分')}
検索結果: {len(all_papers)}件の論文を発見
要約対象: {len(papers)}件を選定
高優先度: {high_priority}件

========================================
📌 本日のハイライト (詳細要約)
========================================"""
    
    def _create_summary_section(self, papers: List[Dict]) -> str:
        """詳細要約セクションの作成
        
        引数:
            papers (List[Dict]): 要約付き論文
            
        戻り値:
            str: 要約セクション
        """
        if not papers:
            return "\\n要約対象の論文がありませんでした。"
        
        high_priority = [p for p in papers if self._is_high_priority(p)]
        medium_priority = [p for p in papers if p not in high_priority]
        
        section = ""
        
        # 高優先度論文
        if high_priority:
            section += "\\n🌟 注目論文\\n\\n"
            for i, paper in enumerate(high_priority, 1):
                section += f"{i}. {paper.get('summary_ja', 'No summary')}\\n\\n"
        
        # その他の論文
        if medium_priority:
            section += "📋 その他の要約論文\\n\\n"
            for i, paper in enumerate(medium_priority, len(high_priority) + 1):
                section += f"{i}. {paper.get('summary_ja', 'No summary')}\\n\\n"
        
        return section
    
    def _create_paper_list_section(
        self, 
        all_papers: List[Dict], 
        summarized_papers: List[Dict]
    ) -> str:
        """完全な論文リストセクションの作成
        
        引数:
            all_papers (List[Dict]): 発見された全論文
            summarized_papers (List[Dict]): 要約された論文
            
        戻り値:
            str: 論文リストセクション
        """
        section = f"""========================================
📋 検索結果一覧 (全{len(all_papers)}件)
========================================

"""
        
        summarized_ids = {p['id'] for p in summarized_papers}
        
        for i, paper in enumerate(all_papers, 1):
            is_summarized = paper['id'] in summarized_ids
            status = "[要約済]" if is_summarized else "[リスト]"
            
            authors_str = self._format_authors(paper.get('authors', []))
            
            # 和訳タイトルを生成
            japanese_title = self._translate_title_to_japanese(paper.get('title', 'No title'))
            
            section += f"""{i}. {status} {paper.get('title', 'No title')}
   和訳: {japanese_title}
   著者: {authors_str}
   投稿日: {paper.get('published', 'Unknown')}
   カテゴリ: {', '.join(paper.get('categories', []))}
   PDF: {paper.get('pdf_url', 'No URL')}
   キーワード: {paper.get('keyword', 'Unknown')}

"""
        
        return section
    
    def _create_footer(self) -> str:
        """メールフッターセクションの作成
        
        戻り値:
            str: フッターセクション
        """
        return f"""========================================
📊 統計情報
========================================

検索キーワード: {', '.join(self.config.SEARCH_KEYWORDS)}
検索期間: 過去{self.config.DAYS_BACK}日間
データソース: arXiv.org
システム: Raspberry Pi 自動論文要約システム

このメールは自動生成されています。
配信停止をご希望の場合はお知らせください。"""
    
    def _format_authors(self, authors: List[str]) -> str:
        """表示用の著者リストのフォーマット
        
        引数:
            authors (List[str]): 著者名のリスト
            
        戻り値:
            str: フォーマットされた著者文字列
        """
        if not authors:
            return "Unknown"
        
        if len(authors) > 3:
            return ', '.join(authors[:3]) + ' ほか'
        else:
            return ', '.join(authors)
    
    def _is_high_priority(self, paper: Dict) -> bool:
        """要約に基づく論文の高優先度チェック
        
        引数:
            paper (Dict): 要約付き論文
            
        戻り値:
            bool: 高優先度の場合はTrue
        """
        summary = paper.get('summary_ja', '')
        return '★★★★★' in summary or '★★★★☆' in summary
    
    def _count_high_priority_papers(self, papers: List[Dict]) -> int:
        """高優先度論文の数をカウント
        
        引数:
            papers (List[Dict]): カウント対象の論文
            
        戻り値:
            int: 高優先度論文の数
        """
        return len([p for p in papers if self._is_high_priority(p)])
    
    def _send_email(self, subject: str, body: str) -> bool:
        """SMTPを使用したメール送信
        
        引数:
            subject (str): メール件名
            body (str): メール本文
            
        戻り値:
            bool: 正常に送信された場合はTrue、そうでなければFalse
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.SENDER_EMAIL
            msg['To'] = ', '.join(self.config.RECIPIENT_EMAILS)
            msg['Subject'] = subject
            
            # Gmail互換性向上のためプレーンテキストとして本文を添付
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # メール送信
            with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.config.SENDER_EMAIL, self.config.SENDER_PASSWORD)
                
                for recipient in self.config.RECIPIENT_EMAILS:
                    if recipient.strip():
                        server.send_message(msg, to_addrs=[recipient.strip()])
            
            return True
            
        except Exception as e:
            self.logger.error(f"SMTP送信エラー: {e}")
            return False
    
    def _validate_email_config(self) -> None:
        """メール設定のバリデーション
        
        例外:
            ValueError: 必要な設定が不足しているか無効な場合
        """
        errors = []
        
        if not self.config.SENDER_EMAIL:
            errors.append("SENDER_EMAIL が必要です")
        elif not self._is_valid_email(self.config.SENDER_EMAIL):
            errors.append("SENDER_EMAIL の形式が無効です")
            
        if not self.config.SENDER_PASSWORD:
            errors.append("SENDER_PASSWORD が必要です")
            
        if not self.config.RECIPIENT_EMAILS:
            errors.append("RECIPIENT_EMAILS が必要です")
        else:
            for email in self.config.RECIPIENT_EMAILS:
                if email.strip() and not self._is_valid_email(email.strip()):
                    errors.append(f"無効な受信者メール: {email}")
        
        if errors:
            error_msg = "メール設定エラー: " + "; ".join(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _is_valid_email(self, email: str) -> bool:
        """メール形式のバリデーション
        
        引数:
            email (str): バリデーション対象のメールアドレス
            
        戻り値:
            bool: 有効なメール形式の場合はTrue
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _translate_title_to_japanese(self, title: str) -> str:
        """英語タイトルの簡易和訳
        
        引数:
            title (str): 英語タイトル
            
        戻り値:
            str: 日本語タイトル（簡易翻訳）
        """
        if not title or title == 'No title':
            return 'タイトルなし'
        
        # 電力・エネルギー分野の専門用語辞書
        translation_dict = {
            # 基本的な電力用語
            'power': '電力',
            'energy': 'エネルギー',
            'electricity': '電気',
            'electric': '電気の',
            'electrical': '電気の',
            'grid': 'グリッド',
            'smart grid': 'スマートグリッド',
            'microgrid': 'マイクログリッド',
            
            # 予測関連
            'forecast': '予測',
            'forecasting': '予測',
            'prediction': '予測',
            'predicting': '予測',
            'estimation': '推定',
            
            # 再生可能エネルギー
            'renewable': '再生可能',
            'solar': '太陽光',
            'wind': '風力',
            'photovoltaic': '太陽光発電',
            'wind power': '風力発電',
            'solar power': '太陽光発電',
            
            # 需要・供給
            'demand': '需要',
            'supply': '供給',
            'load': '負荷',
            'generation': '発電',
            'consumption': '消費',
            
            # AI・機械学習
            'machine learning': '機械学習',
            'deep learning': '深層学習',
            'neural network': 'ニューラルネットワーク',
            'artificial intelligence': '人工知能',
            'ai': 'AI',
            'generative': '生成',
            'transformer': 'トランスフォーマー',
            'lstm': 'LSTM',
            'cnn': 'CNN',
            
            # システム・制御
            'system': 'システム',
            'control': '制御',
            'management': '管理',
            'optimization': '最適化',
            'algorithm': 'アルゴリズム',
            'model': 'モデル',
            'method': '手法',
            'approach': 'アプローチ',
            
            # その他技術用語
            'storage': '蓄電',
            'battery': 'バッテリー',
            'voltage': '電圧',
            'frequency': '周波数',
            'stability': '安定性',
            'efficiency': '効率',
            'performance': '性能',
            'analysis': '解析',
            'monitoring': '監視',
            'real-time': 'リアルタイム',
            
            # 一般的な単語
            'using': 'を用いた',
            'based': 'ベースの',
            'improved': '改良された',
            'enhanced': '強化された',
            'novel': '新しい',
            'efficient': '効率的な',
            'optimal': '最適な',
            'robust': '頑健な',
            'accurate': '精確な',
            'short-term': '短期',
            'long-term': '長期',
            'multi': 'マルチ',
            'multi-step': '多段階',
            'time series': '時系列'
        }
        
        # タイトルを小文字に変換して翻訳
        translated_title = title.lower()
        
        # 専門用語を日本語に置換（長いフレーズから先に処理）
        sorted_terms = sorted(translation_dict.items(), key=lambda x: len(x[0]), reverse=True)
        for english, japanese in sorted_terms:
            translated_title = translated_title.replace(english, japanese)
        
        # 最初の文字を大文字に戻し、不要な記号を整理
        translated_title = translated_title.strip()
        if translated_title:
            translated_title = translated_title[0].upper() + translated_title[1:]
        
        # 翻訳が不完全な場合の簡易修正
        if len([c for c in translated_title if ord(c) > 127]) < len(translated_title) * 0.3:
            # 日本語の割合が少ない場合は元のタイトルを併記
            return f"{translated_title}（原題参照）"
        
        return translated_title


class EmailError(Exception):
    """メール関連エラー用のカスタム例外"""
    pass