# 研究論文自動要約システム 📚⚡

電力・エネルギー・AI分野の最新研究論文を自動収集し、日本語で要約してメール配信するPythonシステムです。

## 🎯 システム概要

このシステムは以下の機能を提供します：

- **自動論文収集**: arXivから電力・エネルギー・AI関連の論文を自動取得
- **AI要約生成**: OpenAI GPT-3.5-turboを使用した日本語要約の生成
- **電力分野特化**: 風力・太陽光発電予測、電力需要予測、スマートグリッド技術に重点
- **メール通知**: Gmail経由での要約レポート自動配信
- **データベース管理**: SQLiteによる論文履歴の永続化

## 🔧 システム要件

### 必要なソフトウェア
- Python 3.8以上
- pip (Pythonパッケージマネージャー)
- インターネット接続

### 必要なAPIキー・アカウント
- **OpenAI APIキー**: 論文要約生成用
- **Gmailアカウント**: メール送信用（アプリパスワード設定必要）

## 📦 インストール手順

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd paper_picker
```

### 2. Python仮想環境の作成
```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows
```

### 3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 4. 設定ファイルの作成
```bash
cp src/.env.example src/.env  # サンプルファイルがある場合
# または手動で src/.env ファイルを作成
```

## ⚙️ 設定方法

### 基本設定 (src/.env)

以下の内容で `src/.env` ファイルを作成してください：

```env
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key_here

# Gmail SMTP設定
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAILS=recipient1@example.com,recipient2@example.com

# 検索設定
MAX_PAPERS=30
SEARCH_KEYWORDS=machine learning,deep learning,prediction,optimization,energy,power

# 日付範囲設定
# 検索モード: 'days_back' または 'date_range'
DATE_SEARCH_MODE=days_back

# モード1: 現在から指定日数分さかのぼる場合
DAYS_BACK=7

# モード2: 日付範囲を指定する場合（YYYY-MM-DD形式）
# DATE_SEARCH_MODE=date_range の場合のみ有効
START_DATE=2024-01-01
END_DATE=2024-12-31
```

### 🔑 設定変更のコツ

#### OpenAI APIキーの取得
1. [OpenAI Platform](https://platform.openai.com/)にアクセス
2. アカウント作成・ログイン
3. API Keys > Create new secret key
4. 生成されたキーを `OPENAI_API_KEY` に設定

#### Gmail設定のポイント
1. **アプリパスワードの設定**:
   - Googleアカウントで2段階認証を有効化
   - アプリパスワードを生成（通常のパスワードではない）
   - 生成されたパスワードを `SENDER_PASSWORD` に設定

2. **セキュリティ設定**:
   - 「安全性の低いアプリのアクセス」は不要（アプリパスワード使用時）
   - SMTP over TLS（ポート587）を使用

#### 検索キーワードの最適化
```env
# 大量収集戦略用の推奨キーワード（幅広い検索）
SEARCH_KEYWORDS=machine learning,deep learning,prediction,forecasting,optimization,artificial intelligence,neural network,energy,power,smart grid

# USER_KEYWORDSで具体的なフィルタリング（config.pyで設定）
# 例: ['prediction', 'machine learning', 'energy forecasting', 'smart grid', 'optimization']
```

#### 日付範囲設定の詳細

**モード1: 日数指定（推奨）**
```env
DATE_SEARCH_MODE=days_back
DAYS_BACK=7  # 過去7日間の論文を検索
```

**モード2: 日付範囲指定**
```env
DATE_SEARCH_MODE=date_range
START_DATE=2024-01-01  # 検索開始日
END_DATE=2024-01-31    # 検索終了日
```

**使い分けのガイドライン:**
- **日常運用**: `days_back`モード（3-7日推奨）
- **過去データ収集**: `date_range`モード（特定期間指定）
- **年次レポート**: `date_range`モード（年間データ）

#### パフォーマンス調整
- `MAX_PAPERS`: 最終要約論文数（5-30推奨）
- 日付範囲が広いほど処理時間とAPI使用量が増加
- 初期収集数は自動で200+件（最終数の10倍）
- 論文数を増やすとOpenAI API使用量が増加

## 🚀 実行方法

### 基本実行
```bash
# 仮想環境の有効化
source venv/bin/activate

# メインスクリプトの実行
python src/main.py
```

### 文字化け対策（必要に応じて）
```bash
export PYTHONIOENCODING=utf-8
python src/main.py
```

### 自動実行設定（cron）
```bash
# crontabの編集
crontab -e

# 毎日9時に実行する例
0 9 * * * cd /path/to/paper_picker && source venv/bin/activate && python src/main.py
```

## 📁 ディレクトリ構造

```
paper_picker/
├── src/                    # ソースコード
│   ├── main.py            # メインエントリーポイント
│   ├── config.py          # 設定管理
│   ├── paper_fetcher.py   # 論文取得
│   ├── llm_summarizer.py  # AI要約生成
│   ├── email_sender.py    # メール送信
│   ├── database.py        # データベース管理
│   └── .env              # 設定ファイル（要作成）
├── data/                   # データディレクトリ
│   └── papers.db          # SQLiteデータベース（自動生成）
├── logs/                   # ログディレクトリ
│   └── system.log         # システムログ（自動生成）
├── venv/                   # Python仮想環境
├── requirements.txt        # Python依存関係
└── README.md              # このファイル
```

## 🔍 論文取得から要約までの詳細フロー

### 📋 全体概要
システムは重複チェック機能を含む7段階の統合パイプラインで動作します：

```
[大量論文収集] → [データベース重複チェック] → [日付フィルタ] → [関連度評価] → [複合スコア算出] → [バランス選択] → [要約生成] → [全論文DB保存] → [メール送信]
```

### 🔍 Step 1: 大量論文収集・取得
**担当モジュール**: `paper_fetcher.py`

1. **検索戦略の革新**
   - 初期収集数を大幅拡大：200+件（最終出力の10倍）
   - 各キーワードから最大100件ずつ取得
   - 関連度フィルタリングを前提とした大量収集戦略

2. **検索条件の構築**
   - `.env`の`SEARCH_KEYWORDS`から検索キーワードを読み込み
   - `config.py`の`USER_KEYWORDS`でフィルタリング
   - シンプルなall:検索で幅広い論文を収集

3. **arXiv API検索**
   - キーワードごとに並列検索実行
   - 投稿日の降順でソート
   - 重複論文は後段で除去

### 🔄 Step 2: データベース重複チェック
**担当モジュール**: `database.py` - `filter_new_papers()`

1. **検索済み論文の除外**
   - 検索結果とデータベースの論文IDを照合
   - 既に処理済みの論文は自動的にスキップ
   - 新規論文のみを後続処理に送信

2. **効率的な処理**
   - 不要な要約処理を回避してAPI使用量を削減
   - 重複論文の配信を防止
   - ログで重複チェック結果を出力

3. **日付範囲と重複チェックの組み合わせ**
   - 日付範囲モードでも重複チェックが機能
   - 過去データ収集時の重複を防止
   - 効率的な差分更新が可能

### 🎯 Step 3-7: 多段階フィルタリングシステム
**担当モジュール**: `paper_fetcher.py` - `_apply_multi_stage_filtering()`

#### Stage 1: 全論文収集
- 各キーワードから取得した論文を統合
- 合計200+件の論文プールを構築

#### Stage 2: 収集時重複除去
- 論文IDベースの重複検出
- ユニークな論文のみを保持

#### Stage 3: 日付フィルタ
- 設定された日付範囲内の論文に絞り込み
- `days_back`モード: 過去指定日数以内の論文
- `date_range`モード: 指定された期間内の論文
- 範囲外の論文を除外して処理効率を向上

#### Stage 4: 関連度による第1次絞り込み
- **6要素関連度スコア算出**（0-100点）：
  1. **タイトルキーワードマッチ**（重み3.0）
  2. **アブストラクトキーワードマッチ**（重み2.0）
  3. **検索キーワード関連性**（重み1.5）
  4. **意味的関連性**（関連語辞書使用）
  5. **カテゴリベース関連性**
  6. **キーワード共起スコア**

- 関連度30点以上の論文を保持
- 上位30-50%まで絞り込み（最大100件）

#### Stage 5: 複合スコアによる第2次絞り込み
- **複合スコア算出**：
  ```
  複合スコア = 関連度60% + 重要度30% + 新しさ10%
  ```
- **重要度スコア**（0-100点）の内訳：
  - 著者数評価（適度な共同研究を優遇）
  - 技術キーワード密度
  - アブストラクト品質
  - arXivカテゴリ重要度
  - 論文年数バランス
  - エネルギー分野キーワードボーナス

#### Stage 6: キーワードバランス最終選択
- `USER_KEYWORDS`間での均等選択
- 各キーワードから複合スコア順に選択
- 最終的に`MAX_PAPERS`件（デフォルト30件）に絞り込み

### 🤖 Step 8: AI要約生成  
**担当モジュール**: `llm_summarizer.py`

1. **重要度ベース処理順序**
   - 選択された論文を重要度スコア順にソート
   - 高重要度論文（80点以上）は詳細な要約を生成
   - 各論文の重要度・関連度スコアをログ出力

2. **USER_KEYWORDSベースの関連度チェック**
   - `config.py`の`USER_KEYWORDS`との照合
   - 関連度の低い論文は要約をスキップ
   - キーワードマッチングによる効率的な処理

3. **適応的プロンプト構築**
   ```
   【重要度80+】詳細な要約指示
   【重要度60-79】標準的な要約指示
   【重要度59以下】簡潔な要約指示
   
   【出力形式】
   📄 タイトル + PDFリンク
   🎯 研究の背景・目的
   🔬 提案手法  
   📊 主な成果・結果
   💡 電力分野への応用
   ⭐ 電力分野重要度 (5段階評価)
   🔍 注目ポイント（6つの技術領域別）
   ```

4. **OpenAI API呼び出し**
   - モデル: `gpt-4o-mini`
   - 最大1500トークン
   - 温度: 0.3（一貫性重視）
   - リトライ機能付き（最大3回）
   - PDFリンク保護システム

### 💾 Step 9: 全論文データベース保存
**担当モジュール**: `database.py` - `save_papers()`, `main.py` - `prepare_papers_for_database()`

1. **統合データベース戦略**
   - **要約対象論文**: 日本語要約付きでDB保存
   - **要約対象外論文**: 要約フィールドは空でDB保存
   - **全配信論文**: 最終的にリスト配信される全ての論文をDB登録

2. **SQLiteテーブル構造**
   ```sql
   CREATE TABLE papers (
       id TEXT PRIMARY KEY,
       title TEXT NOT NULL,
       authors TEXT,
       abstract TEXT,
       summary_ja TEXT,              -- 要約対象外では空文字
       published DATE,
       pdf_url TEXT,
       categories TEXT,
       keyword TEXT,
       processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. **保存処理フロー**
   - 要約済み論文と要約なし論文を統合
   - `prepare_papers_for_database()`で統合リスト作成
   - INSERT OR REPLACE文で効率的な保存
   - トランザクション処理で一括保存

### 📧 Step 10: メール配信
**担当モジュール**: `email_sender.py`

1. **メール構成**
   ```
   件名: 📚 研究論文要約レポート - YYYY年MM月DD日
   
   [ヘッダー] 統計情報（発見/要約/重要度分布）
   [要約セクション] 重要度順の論文要約
   [リストセクション] 全論文リスト（スコア付き）
   [フッター] 検索条件・フィルタリング統計
   ```

2. **重要度ベースの表示**
   - 高重要度論文を優先表示
   - 各論文の重要度・関連度スコアを表示
   - バランス選択の結果を統計情報として提供

3. **Gmail最適化**
   - プレーンテキスト形式
   - 適切な改行・セクション分け
   - 絵文字による視認性向上

### 📊 処理統計・ログ出力

実行時に以下の詳細情報が`logs/system.log`に記録されます：

```
# 論文収集段階
初期検索で200件の論文を収集します...

# データベース重複チェック段階
データベースとの重複チェックを実行しています...
重複チェック完了: 245件中47件が既存、198件が新規論文

# 多段階フィルタリング段階
Stage 1: 全198件の論文を収集
Stage 2: 収集時重複除去後186件
Stage 3: 日付フィルタ後156件
Stage 4: 関連度フィルタ後78件
Stage 5: 複合スコアフィルタ後45件
Stage 6: 最終選択30件

# スコア分布統計
選択論文スコア分布: 関連度平均72.3(最高95.2), 重要度平均64.1(最高88.7), 高関連度論文18件

# 要約処理段階
論文要約中 1/30 (重要度:88.7, 関連度:95.2): Advanced AI-Based Wind Power Forecasting...
論文要約中 2/30 (重要度:84.3, 関連度:87.9): Deep Learning for Solar Energy Prediction...

# データベース保存段階
DB保存対象論文: 要約あり30件, 要約なし168件, 合計198件
データベース保存が完了しました: 198件の論文

# 実行終了時
=== 処理完了 ===
発見論文総数: 245件（新規論文: 198件）
要約済み論文: 30件  
成功した要約: 28件
DB保存論文総数: 198件
```

### ⚙️ 設定による動作調整

| 設定項目 | 影響する処理 | 推奨値 | 新機能での効果 |
|---------|-------------|--------|---------------|
| `SEARCH_KEYWORDS` | Stage1の初期検索範囲 | 幅広いキーワード | 大量収集戦略で検索範囲拡大 |
| `USER_KEYWORDS` | Stage4-6の関連度評価 | 特化したキーワード | バランス選択とフィルタリング |
| `DATE_SEARCH_MODE` | 日付範囲決定方式 | `days_back` | 日常運用 vs 過去データ収集 |
| `DAYS_BACK` | days_backモードの期間 | 3-7日 | 効率的な期間絞り込み |
| `START_DATE/END_DATE` | date_rangeモードの期間 | 必要な期間 | 過去データの柔軟な収集 |
| `MAX_PAPERS` | Stage6の最終選択数 | 5-30件 | 多段階フィルタ後の出力数 |
| OpenAI APIキー | Step8の要約品質 | 有効なキー | 重要度ベース適応的要約 |

### 🚀 システムの革新ポイント

#### 1. **検索戦略の革新**
- **従来**: 各キーワード10-20件 → **現在**: 各キーワード最大100件
- **効果**: 関連度の高い論文を見逃すリスクを大幅削減

#### 2. **効率的な重複管理**
- **データベース重複チェック**: 既存論文の自動スキップ
- **API使用量最適化**: 不要な要約処理を回避
- **履歴管理**: 全配信論文の永続的な追跡

#### 3. **統合データベース戦略**
- **全論文保存**: 要約対象・対象外問わず全配信論文をDB登録
- **条件付き要約**: 要約対象外論文は空の要約フィールドで保存
- **効率的な検索**: 論文IDベースの高速重複チェック

#### 4. **多段階フィルタリング**
- **7段階のインテリジェントな絞り込み**
- **Stage 4-5**: 関連度・重要度・新しさの複合評価
- **Stage 6**: キーワードバランスを考慮した最終選択

#### 5. **高精度スコアリング**
- **関連度スコア**: 6要素による包括的評価
- **重要度スコア**: 電力分野特化の評価指標
- **複合スコア**: 3つの要素のバランス調整

この統合的なデータベース管理と重複チェック機能により、電力・エネルギー分野に特化した高効率な論文要約システムを実現しています。

## ⚠️ トラブルシューティング

### よくある問題と解決方法

#### 1. ModuleNotFoundError
```bash
# 解決方法: 仮想環境の有効化を確認
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. OpenAI API エラー
- APIキーの有効性を確認
- API使用量・残高を確認
- モデル名が正しいか確認（gpt-3.5-turbo）

#### 3. メール送信エラー
- アプリパスワードが正しく設定されているか確認
- 2段階認証が有効になっているか確認
- SMTP設定（サーバー、ポート）を確認

#### 4. 文字化け
```bash
# Linux/Mac
export PYTHONIOENCODING=utf-8

# または.bashrcに追加
echo 'export PYTHONIOENCODING=utf-8' >> ~/.bashrc
```

#### 5. データベースエラー
- `data/` ディレクトリの権限を確認
- SQLiteファイルの書き込み権限を確認

#### 6. 論文が見つからない
- インターネット接続を確認
- 検索キーワードを調整
- 日付範囲を調整:
  - `days_back`モード: `DAYS_BACK`を増加（より長期間を検索）
  - `date_range`モード: 期間を拡大または最近の日付に変更
- `DATE_SEARCH_MODE`の設定値を確認

### ログの確認
```bash
# システムログの確認
tail -f logs/system.log

# エラーログの確認
grep ERROR logs/system.log

# systemdサービスログの確認（サービス設定時）
journalctl -u paper-picker.service -f
journalctl -u paper-picker.timer -f
```

## 🎛️ カスタマイズ方法

### 検索対象分野の変更
`src/paper_fetcher.py` の `categories` リストを編集：
```python
categories = [
    'cs.AI',        # 人工知能
    'cs.LG',        # 機械学習
    'eess.SP',      # 信号処理
    # 必要に応じて追加・削除
]
```

### 要約フォーマットの変更
`src/llm_summarizer.py` の `_create_summary_prompt` メソッドを編集

### メール形式の変更
`src/email_sender.py` の各 `_create_*_section` メソッドを編集

## 📊 使用統計

システム実行後、以下の統計情報がログに記録されます：
- 発見論文総数（新規・既存の内訳）
- データベース重複チェック結果
- 要約済み論文数
- 成功した要約数
- DB保存論文総数（要約あり・なしの内訳）
- 高優先度論文数

## 🔧 新機能：日付範囲モードと重複チェック

### 柔軟な日付範囲検索
- **days_backモード**: 従来の日数指定方式（日常運用推奨）
- **date_rangeモード**: 特定期間指定方式（過去データ収集用）
- **効果**: 過去の論文の効率的な収集、年次レポート作成に対応

### データベース重複チェック機能
- **効果**: 既存論文の再処理を防ぎ、API使用量を大幅削減
- **仕組み**: 論文IDベースでデータベースと照合、新規論文のみ処理
- **date_rangeモード対応**: 過去データ収集時の重複も防止

### 全論文データベース保存
- **要約対象論文**: `summary_ja`フィールドに日本語要約を保存
- **要約対象外論文**: `summary_ja`フィールドは空文字で保存
- **履歴管理**: 全配信論文の完全な追跡が可能

### 使用例
```bash
# 日常運用（過去1週間）
DATE_SEARCH_MODE=days_back
DAYS_BACK=7

# 年次レポート用（2024年全体）
DATE_SEARCH_MODE=date_range
START_DATE=2024-01-01
END_DATE=2024-12-31

# 特定イベント期間の論文収集
DATE_SEARCH_MODE=date_range
START_DATE=2024-06-01
END_DATE=2024-06-30
```

### メンテナンス
```bash
# データベースファイルサイズ確認
ls -lh data/papers.db

# 古いレコードの手動削除（必要に応じて）
sqlite3 data/papers.db "DELETE FROM papers WHERE processed_at < DATE('now', '-365 days');"

# 日付範囲でのデータ確認
sqlite3 data/papers.db "SELECT COUNT(*), MIN(published), MAX(published) FROM papers;"
```

