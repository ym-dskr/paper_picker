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
        
        return f"{header}\n\n{summary_section}\n\n{paper_list_section}\n\n{footer}"
    
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
            return "\n要約対象の論文がありませんでした。"
        
        high_priority = [p for p in papers if self._is_high_priority(p)]
        medium_priority = [p for p in papers if p not in high_priority]
        
        section = ""
        
        # 高優先度論文
        if high_priority:
            section += "\n🌟 注目論文\n\n"
            for i, paper in enumerate(high_priority, 1):
                section += f"{i}. {paper.get('summary_ja', 'No summary')}\n\n"
        
        # その他の論文
        if medium_priority:
            section += "📋 その他の要約論文\n\n"
            for i, paper in enumerate(medium_priority, len(high_priority) + 1):
                section += f"{i}. {paper.get('summary_ja', 'No summary')}\n\n"
        
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
        """英語タイトルの高精度和訳
        
        引数:
            title (str): 英語タイトル
            
        戻り値:
            str: 日本語タイトル（改良版翻訳）
        """
        if not title or title == 'No title':
            return 'タイトルなし'
        
        # AI・電力・IoT分野の専門用語辞書（改良版）
        translation_dict = {
            # AI×電力融合用語（優先度最高）
            'machine learning power forecast': '機械学習による電力予測',
            'deep learning energy prediction': '深層学習によるエネルギー予測',
            'ai renewable energy forecast': 'AI再生可能エネルギー予測',
            'smart grid ai': 'スマートグリッドAI',
            'generative ai energy': '生成AI エネルギー',
            'neural network demand forecast': 'ニューラルネットワーク需要予測',
            'iot energy management': 'IoTエネルギー管理',
            'edge computing power': 'エッジコンピューティング電力',
            'digital twin energy': 'デジタルツイン エネルギー',
            
            # 電力・エネルギー専門用語
            'wind power forecast': '風力発電予測',
            'solar power forecast': '太陽光発電予測', 
            'photovoltaic forecast': '太陽光発電予測',
            'renewable energy forecast': '再生可能エネルギー予測',
            'electricity demand forecast': '電力需要予測',
            'power demand forecast': '電力需要予測',
            'load forecast': '負荷予測',
            'energy storage': 'エネルギー貯蔵',
            'battery energy storage': 'バッテリーエネルギー貯蔵',
            'smart grid': 'スマートグリッド',
            'microgrid': 'マイクログリッド',
            'power system': '電力システム',
            'energy management': 'エネルギー管理',
            'grid optimization': 'グリッド最適化',
            
            # AI・機械学習用語
            'machine learning': '機械学習',
            'deep learning': '深層学習',
            'neural network': 'ニューラルネットワーク',
            'artificial intelligence': '人工知能',
            'generative ai': '生成AI',
            'transformer': 'トランスフォーマー',
            'lstm': 'LSTM',
            'reinforcement learning': '強化学習',
            'time series': '時系列',
            'prediction model': '予測モデル',
            'forecasting model': '予測モデル',
            'anomaly detection': '異常検知',
            'pattern recognition': 'パターン認識',
            
            # IoT・技術基盤用語
            'internet of things': 'モノのインターネット',
            'iot': 'IoT',
            'edge computing': 'エッジコンピューティング',
            'sensor network': 'センサーネットワーク',
            'smart sensor': 'スマートセンサー',
            'real-time monitoring': 'リアルタイム監視',
            'cyber-physical system': 'サイバー物理システム',
            'digital twin': 'デジタルツイン',
            'federated learning': '連合学習',
            
            # 基本的な電力用語
            'power': '電力',
            'energy': 'エネルギー',
            'electricity': '電気',
            'electric': '電気の',
            'electrical': '電気の',
            'grid': 'グリッド',
            'renewable': '再生可能',
            'solar': '太陽光',
            'wind': '風力',
            'photovoltaic': '太陽光発電',
            'battery': 'バッテリー',
            'storage': '蓄電',
            'generation': '発電',
            'load': '負荷',
            'demand': '需要',
            'supply': '供給',
            'voltage': '電圧',
            'frequency': '周波数',
            'stability': '安定性',
            
            # 予測・分析関連
            'forecast': '予測',
            'forecasting': '予測',
            'prediction': '予測',
            'predicting': '予測',
            'estimation': '推定',
            
            # システム・制御・分析用語
            'system': 'システム',
            'control': '制御',
            'management': '管理',
            'optimization': '最適化',
            'algorithm': 'アルゴリズム',
            'model': 'モデル',
            'method': '手法',
            'approach': 'アプローチ',
            'analysis': '解析',
            'monitoring': '監視',
            'efficiency': '効率',
            'performance': '性能',
            
            # 技術修飾語
            'using': 'を用いた',
            'based': 'ベースの',
            'improved': '改良された',
            'enhanced': '強化された',
            'novel': '新しい',
            'efficient': '効率的な',
            'optimal': '最適な',
            'robust': '頑健な',
            'accurate': '精確な',
            'real-time': 'リアルタイム',
            'short-term': '短期',
            'long-term': '長期',
            'multi-step': '多段階'
        }
        
        # 高品質翻訳処理
        result = self._perform_high_quality_translation(title, translation_dict)
        return result
    
    def _perform_high_quality_translation(self, title: str, translation_dict: dict) -> str:
        """高品質な翻訳処理を実行
        
        引数:
            title (str): 原題
            translation_dict (dict): 翻訳辞書
            
        戻り値:
            str: 翻訳されたタイトル
        """
        if not title:
            return 'タイトルなし'
        
        # 元のタイトルを保持
        original_title = title
        translated_title = title.lower()
        
        # 専門用語を日本語に置換（長いフレーズから先に処理）
        sorted_terms = sorted(translation_dict.items(), key=lambda x: len(x[0]), reverse=True)
        for english, japanese in sorted_terms:
            if english in translated_title:
                translated_title = translated_title.replace(english, japanese)
        
        # 翻訳品質の評価
        japanese_char_count = len([c for c in translated_title if ord(c) > 127])
        total_char_count = len(translated_title)
        japanese_ratio = japanese_char_count / total_char_count if total_char_count > 0 else 0
        
        # 翻訳品質に基づく出力決定
        if japanese_ratio >= 0.4:
            # 十分な日本語化が達成された場合
            # 文頭を大文字化し、整形
            if translated_title:
                translated_title = translated_title.strip()
                if translated_title and translated_title[0].isalpha():
                    translated_title = translated_title[0].upper() + translated_title[1:]
            return translated_title
        elif japanese_ratio >= 0.2:
            # 部分的な翻訳の場合
            translated_title = translated_title.strip()
            if translated_title and translated_title[0].isalpha():
                translated_title = translated_title[0].upper() + translated_title[1:]
            return f"{translated_title}（部分和訳）"
        else:
            # 翻訳が不十分な場合は意訳を試行
            simplified_translation = self._create_simplified_translation(original_title)
            return simplified_translation
    
    def _create_simplified_translation(self, title: str) -> str:
        """翻訳困難なタイトルの意訳生成
        
        引数:
            title (str): 原題
            
        戻り値:
            str: 意訳または原題併記
        """
        # キーワードベースの意訳
        title_lower = title.lower()
        
        # 分野判定
        if any(word in title_lower for word in ['power', 'energy', 'electricity', 'grid']):
            if any(word in title_lower for word in ['forecast', 'prediction', 'predict']):
                return f"電力・エネルギー予測技術の研究（原題：{title[:50]}...）"
            elif any(word in title_lower for word in ['ai', 'machine learning', 'deep learning']):
                return f"AI・機械学習を用いた電力技術（原題：{title[:50]}...）"
            else:
                return f"電力・エネルギー分野の技術研究（原題：{title[:50]}...）"
        elif any(word in title_lower for word in ['machine learning', 'ai', 'neural', 'deep learning']):
            return f"AI・機械学習技術の研究（原題：{title[:50]}...）"
        elif any(word in title_lower for word in ['iot', 'sensor', 'monitoring']):
            return f"IoT・センシング技術の研究（原題：{title[:50]}...）"
        else:
            # タイトルが長すぎる場合は短縮
            short_title = title[:60] + "..." if len(title) > 60 else title
            return f"技術研究論文（原題：{short_title}）"


class EmailError(Exception):
    """メール関連エラー用のカスタム例外"""
    pass