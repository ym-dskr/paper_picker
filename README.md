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
MAX_PAPERS=5
SEARCH_KEYWORDS=wind power forecast,solar power forecast,electricity demand forecast,smart grid AI
DAYS_BACK=2
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
# 電力分野特化の推奨キーワード
SEARCH_KEYWORDS=wind power forecast,solar power forecast,photovoltaic forecast,electricity demand forecast,energy demand prediction,renewable energy forecast,power load forecast,smart grid AI,generative AI energy,battery energy storage,grid optimization,electricity price forecast,distributed energy resources,microgrid control,energy management system
```

#### パフォーマンス調整
- `MAX_PAPERS`: 要約する論文数（1-10推奨）
- `DAYS_BACK`: 検索期間（1-7日推奨）
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
システムは5つの主要ステップで動作します：

```
[論文検索] → [関連度評価] → [要約生成] → [データ保存] → [メール送信]
```

### 🔍 Step 1: 論文検索・取得
**担当モジュール**: `paper_fetcher.py`

1. **検索条件の構築**
   - `.env`の`SEARCH_KEYWORDS`から検索キーワードを読み込み
   - 電力関連キーワード（power, energy, grid等）を検出
   - 対象カテゴリを動的に選択：
     ```python
     # 電力関連の場合：広範囲カテゴリ
     ['cs.AI', 'cs.LG', 'eess.SP', 'eess.SY', 'math.OC', 'stat.AP', ...]
     
     # AI関連の場合：AI特化カテゴリ
     ['cs.AI', 'cs.LG', 'cs.CV', 'cs.NE', 'stat.ML']
     ```

2. **arXiv API検索**
   - キーワードごとに並列検索実行
   - 投稿日の降順でソート
   - 過去`DAYS_BACK`日以内の論文に絞り込み
   - 重複論文の自動除去

3. **取得結果**
   - 論文メタデータ（タイトル、著者、アブストラクト、PDF URL等）
   - 最大100件取得後、関連度評価で絞り込み

### 🎯 Step 2: 電力分野関連度評価
**担当モジュール**: `llm_summarizer.py` - `_assess_power_relevance()`

1. **4段階キーワードベース評価**
   ```python
   # 最高関連度（重み0.4）- AI×予測×電力融合技術
   ['ai power forecast', 'machine learning energy prediction', 'smart grid ai', 
    'generative ai energy', 'iot energy management', 'digital twin energy', ...]
   
   # 高関連度（重み0.3）- 電力予測・IoT特化  
   ['power forecast', 'renewable energy forecast', 'iot power monitoring',
    'smart meter', 'real-time power prediction', ...]
   
   # 中関連度（重み0.2）- AI・予測技術一般
   ['machine learning', 'deep learning', 'prediction model', 'lstm',
    'anomaly detection', 'predictive analytics', ...]
    
   # IoT基盤（重み0.15）- IoT・技術基盤
   ['internet of things', 'edge computing', 'sensor network', 
    'cyber-physical system', 'federated learning', ...]
   ```

2. **スコア計算**
   - タイトル + アブストラクトでキーワードマッチング
   - 各カテゴリの重みを合計してスコア算出
   - 0.0-1.0の範囲で正規化

3. **フィルタリング**
   - スコア0.3未満の論文は要約対象外
   - 高関連度論文のみが次のステップへ

### 🤖 Step 3: AI要約生成  
**担当モジュール**: `main.py` → `llm_summarizer.py`

1. **要約対象選定（新機能）**
   - 全論文の電力関連度を事前評価
   - 関連度スコア順（降順）にソート
   - 関連度0.3以上の論文から`MAX_PAPERS`件を選定
   - 上位5件の関連度スコアをログ出力

2. **プロンプト構築**
   ```
   【システムプロンプト】
   電力システム・エネルギー予測・AI技術の専門研究者として要約
   
   【出力形式】
   📄 タイトル
   🎯 研究の背景・目的
   🔬 提案手法  
   📊 主な成果・結果
   💡 電力分野への応用
   ⭐ 電力分野重要度 (5段階評価)
   🔍 注目ポイント（6つの技術領域別）
   ```

3. **OpenAI API呼び出し**
   - モデル: `gpt-3.5-turbo`
   - 最大1500トークン
   - 温度: 0.3（一貫性重視）
   - リトライ機能付き（最大3回）

4. **品質検証**
   - 生成要約の文字数チェック（50文字以上）
   - 空要約の検出と除外

### 💾 Step 4: データベース保存
**担当モジュール**: `database.py`

1. **SQLiteテーブル構造**
   ```sql
   CREATE TABLE papers (
       id TEXT PRIMARY KEY,
       title TEXT NOT NULL,
       authors TEXT,
       abstract TEXT,
       published DATE,
       pdf_url TEXT,
       categories TEXT,
       keyword TEXT,
       summary_ja TEXT,
       summary_generated BOOLEAN,
       power_relevance REAL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **保存処理**
   - 論文IDによる重複チェック
   - トランザクション処理で一括保存
   - エラー時の自動ロールバック

### 📧 Step 5: メール配信
**担当モジュール**: `email_sender.py`

1. **メール構成**
   ```
   件名: 📚 研究論文要約レポート - YYYY年MM月DD日
   
   [ヘッダー] 統計情報（発見/要約/高優先度件数）
   [要約セクション] 🌟注目論文 + 📋その他要約論文
   [リストセクション] 全論文リスト（和訳タイトル付き）
   [フッター] 検索条件・統計情報
   ```

2. **和訳タイトル生成**
   - 60+の電力・AI専門用語辞書
   - 長いフレーズ優先の置換処理
   - 翻訳品質の自動判定

3. **Gmail最適化**
   - プレーンテキスト形式
   - 適切な改行・セクション分け
   - 絵文字による視認性向上

### 📊 処理統計・ログ出力

実行時に以下の詳細情報が`logs/system.log`に記録されます：

```
# 関連度評価段階
45件の論文の電力関連度を評価しています...
上位5件の論文関連度スコア:
  1. スコア0.850: Advanced Wind Power Forecasting Using Deep Learning...
  2. スコア0.720: Solar Power Generation Prediction with Machine Learning...
  3. スコア0.650: Smart Grid Optimization Using Reinforcement Learning...
  4. スコア0.580: Electricity Demand Forecasting with LSTM Networks...
  5. スコア0.420: Battery Energy Storage System Control Strategy...
高関連度論文: 12件, 低関連度論文: 33件

# 要約選定段階  
関連度0.3以上の論文12件から上位5件を要約対象に選定

# 実行終了時
=== 処理完了 ===
発見論文総数: 45件
要約済み論文: 5件  
成功した要約: 5件
高優先度論文: 3件
```

### ⚙️ 設定による動作調整

| 設定項目 | 影響する処理 | 推奨値 |
|---------|-------------|--------|
| `SEARCH_KEYWORDS` | Step1の検索範囲 | 電力特化キーワード |
| `DAYS_BACK` | Step1の期間絞り込み | 1-7日 |
| `MAX_PAPERS` | Step3の要約対象数 | 3-10件 |
| OpenAI APIキー | Step3の要約品質 | 有効なキー |

この詳細フローにより、電力分野に特化した高品質な論文要約システムを実現しています。

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
- `DAYS_BACK` を増加（より長期間を検索）

### ログの確認
```bash
# システムログの確認
tail -f logs/system.log

# エラーログの確認
grep ERROR logs/system.log
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
- 発見論文総数
- 要約済み論文数
- 成功した要約数
- 高優先度論文数

