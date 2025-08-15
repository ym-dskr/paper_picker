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
        translation_cache (dict): タイトル翻訳キャッシュ
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
        self.translation_cache = {}  # タイトル翻訳キャッシュ
        
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
                summary = paper.get('summary_ja', 'No summary')
                pdf_url = paper.get('pdf_url', 'No URL')
                
                # 要約にPDFリンクが含まれていない場合は追加
                if '📎 PDF:' not in summary and pdf_url != 'No URL':
                    summary += f"\n\n📎 論文PDF: {pdf_url}\n   ↑ クリックで論文を開く"
                
                section += f"{i}. {summary}\n\n"
        
        # その他の論文
        if medium_priority:
            section += "📋 その他の要約論文\n\n"
            for i, paper in enumerate(medium_priority, len(high_priority) + 1):
                summary = paper.get('summary_ja', 'No summary')
                pdf_url = paper.get('pdf_url', 'No URL')
                
                # 要約にPDFリンクが含まれていない場合は追加
                if '📎 PDF:' not in summary and pdf_url != 'No URL':
                    summary += f"\n\n📎 論文PDF: {pdf_url}\n   ↑ クリックで論文を開く"
                
                section += f"{i}. {summary}\n\n"
        
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
        
        # 全論文のタイトルを事前にバッチ翻訳
        self._batch_translate_titles(all_papers)
        
        summarized_ids = {p['id'] for p in summarized_papers}
        
        for i, paper in enumerate(all_papers, 1):
            is_summarized = paper['id'] in summarized_ids
            status = "[要約済]" if is_summarized else "[リスト]"
            
            authors_str = self._format_authors(paper.get('authors', []))
            
            # キャッシュから和訳タイトルを取得
            japanese_title = self._get_cached_translation(paper.get('title', 'No title'))
            
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
    
    def _batch_translate_titles(self, papers: List[Dict]) -> None:
        """論文タイトルのバッチ翻訳（API呼び出し最適化）
        
        引数:
            papers (List[Dict]): 翻訳対象の論文リスト
        """
        # キャッシュに無いタイトルのみを抽出
        titles_to_translate = []
        for paper in papers:
            title = paper.get('title', 'No title')
            if title not in self.translation_cache and title != 'No title':
                titles_to_translate.append(title)
        
        if not titles_to_translate:
            self.logger.debug("全タイトルがキャッシュ済みです")
            return
        
        self.logger.info(f"{len(titles_to_translate)}件のタイトルをバッチ翻訳します")
        
        try:
            import openai
            
            # APIキーが設定されているかチェック
            if not hasattr(self.config, 'OPENAI_API_KEY') or not self.config.OPENAI_API_KEY:
                self.logger.warning("OpenAI APIキーが未設定のため、フォールバック翻訳を使用します")
                for title in titles_to_translate:
                    self.translation_cache[title] = self._create_fallback_translation(title)
                return
            
            # 大量のタイトルは分割処理（API制限対応）
            batch_size = 15  # 1回のAPI呼び出しで処理する最大件数
            
            for i in range(0, len(titles_to_translate), batch_size):
                batch_titles = titles_to_translate[i:i+batch_size]
                self.logger.info(f"バッチ {i//batch_size + 1}: {len(batch_titles)}件のタイトルを翻訳中...")
                
                # バッチごとに翻訳処理
                self._translate_batch_chunk(batch_titles)
                
                # API制限対応の待機（複数バッチの場合）
                if i + batch_size < len(titles_to_translate):
                    import time
                    time.sleep(1)  # 1秒待機
            
        except Exception as e:
            self.logger.warning(f"バッチ翻訳に失敗しました: {e}")
            # フォールバック翻訳でキャッシュを埋める
            for title in titles_to_translate:
                self.translation_cache[title] = self._create_fallback_translation(title)
    
    def _translate_batch_chunk(self, titles: List[str]) -> None:
        """小さなバッチでの翻訳処理
        
        引数:
            titles (List[str]): 翻訳対象のタイトルリスト（15件以下）
        """
        try:
            import openai
            
            # バッチサイズに応じてmax_tokensを調整
            max_tokens = min(2000, len(titles) * 50 + 200)  # 1タイトルあたり50トークン + 余裕
            
            titles_text = '\n'.join([f"{i+1}. {title}" for i, title in enumerate(titles)])
            
            prompt = f"""以下の英語論文タイトルを、電力・エネルギー・AI・IoT分野の専門用語を正確に反映した自然な日本語に翻訳してください。

英語タイトル一覧:
{titles_text}

翻訳時の注意点：
- 各タイトルを番号付きで翻訳
- 専門用語は適切な日本語技術用語に翻訳
- 「機械学習」「深層学習」「風力発電」「太陽光発電」「電力需要予測」等の標準的な日本語表記を使用
- 簡潔で読みやすい日本語に
- 原題の技術的ニュアンスを保持

出力形式:
1. [1番目のタイトルの日本語翻訳]
2. [2番目のタイトルの日本語翻訳]
...
{len(titles)}. [最後のタイトルの日本語翻訳]"""

            openai.api_key = self.config.OPENAI_API_KEY
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは電力・エネルギー・AI分野の専門翻訳者です。英語論文タイトルを正確で自然な日本語に翻訳してください。すべてのタイトルを番号順に翻訳してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,
                timeout=45
            )
            
            translations = response.choices[0].message.content.strip()
            
            # 翻訳結果をパース
            self._parse_batch_translations(titles, translations)
            
        except Exception as e:
            self.logger.warning(f"バッチチャンク翻訳に失敗しました: {e}")
            # フォールバック翻訳でキャッシュを埋める
            for title in titles:
                self.translation_cache[title] = self._create_fallback_translation(title)
    
    def _parse_batch_translations(self, original_titles: List[str], translations: str) -> None:
        """バッチ翻訳結果をパースしてキャッシュに保存
        
        引数:
            original_titles (List[str]): 元のタイトルリスト
            translations (str): LLMからの翻訳結果
        """
        try:
            lines = translations.split('\n')
            translated_titles = []
            
            # 番号パターンを幅広く検出
            import re
            number_pattern = re.compile(r'^(\d+)\.\s*(.+)$')
            
            for line in lines:
                line = line.strip()
                if line:
                    match = number_pattern.match(line)
                    if match:
                        number = int(match.group(1))
                        translated = match.group(2).strip()
                        
                        # リストのインデックスに合わせて挿入
                        while len(translated_titles) < number:
                            translated_titles.append("")
                        
                        if number <= len(translated_titles):
                            translated_titles[number - 1] = translated
                        else:
                            translated_titles.append(translated)
            
            self.logger.debug(f"パース結果: {len(translated_titles)}件の翻訳を検出")
            
            # 元のタイトルと翻訳結果をマッピング
            successful_translations = 0
            for i, original_title in enumerate(original_titles):
                if i < len(translated_titles) and translated_titles[i]:
                    translated = translated_titles[i]
                    # 翻訳品質チェック
                    if len(translated) > 200:
                        translated = translated[:200] + "..."
                    if len(translated) >= 5:
                        self.translation_cache[original_title] = translated
                        successful_translations += 1
                        self.logger.debug(f"翻訳成功 {i+1}: {original_title[:30]}... → {translated[:30]}...")
                    else:
                        self.logger.warning(f"翻訳品質不良 {i+1}: '{translated}'")
                        self.translation_cache[original_title] = self._create_fallback_translation(original_title)
                else:
                    self.logger.warning(f"翻訳欠落 {i+1}: {original_title[:30]}...")
                    self.translation_cache[original_title] = self._create_fallback_translation(original_title)
            
            self.logger.info(f"バッチ翻訳完了: {successful_translations}/{len(original_titles)}件成功")
                    
        except Exception as e:
            self.logger.warning(f"翻訳結果のパースに失敗しました: {e}")
            self.logger.debug(f"翻訳結果内容: {translations[:500]}...")
            # フォールバックで処理
            for title in original_titles:
                self.translation_cache[title] = self._create_fallback_translation(title)
    
    def _get_cached_translation(self, title: str) -> str:
        """キャッシュからタイトル翻訳を取得
        
        引数:
            title (str): 英語タイトル
            
        戻り値:
            str: 日本語翻訳（キャッシュまたは新規翻訳）
        """
        if title in self.translation_cache:
            return self.translation_cache[title]
        
        # キャッシュに無い場合は個別翻訳
        translated = self._translate_title_with_llm(title)
        self.translation_cache[title] = translated
        return translated

    def _translate_title_with_llm(self, title: str) -> str:
        """個別タイトル翻訳（フォールバック用）
        
        引数:
            title (str): 英語論文タイトル
            
        戻り値:
            str: 日本語翻訳されたタイトル
        """
        if not title or title == 'No title':
            return 'タイトルなし'
        
        # 基本的にはフォールバック翻訳を使用（API呼び出し削減）
        self.logger.debug(f"個別翻訳をフォールバックで処理: {title[:30]}...")
        return self._create_fallback_translation(title)
    
    def _create_fallback_translation(self, title: str) -> str:
        """LLM翻訳失敗時のフォールバック翻訳
        
        引数:
            title (str): 原題
            
        戻り値:
            str: フォールバック翻訳
        """
        title_lower = title.lower()
        
        # 分野別の簡易翻訳
        if any(word in title_lower for word in ['wind power forecast', 'solar power forecast']):
            if 'wind' in title_lower:
                return f"風力発電予測に関する研究: {title[:40]}..."
            else:
                return f"太陽光発電予測に関する研究: {title[:40]}..."
        elif any(word in title_lower for word in ['power forecast', 'demand forecast']):
            return f"電力需要予測に関する研究: {title[:40]}..."
        elif any(word in title_lower for word in ['machine learning', 'deep learning', 'ai']):
            if any(word in title_lower for word in ['power', 'energy']):
                return f"AI・機械学習による電力技術: {title[:40]}..."
            else:
                return f"AI・機械学習技術: {title[:40]}..."
        elif any(word in title_lower for word in ['smart grid', 'microgrid']):
            return f"スマートグリッド技術: {title[:40]}..."
        elif any(word in title_lower for word in ['iot', 'sensor']):
            return f"IoT・センサー技術: {title[:40]}..."
        else:
            return f"技術研究: {title[:50]}..."


class EmailError(Exception):
    """メール関連エラー用のカスタム例外"""
    pass