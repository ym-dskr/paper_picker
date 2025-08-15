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

## 🔍 システムの動作フロー

1. **論文検索**: arXivから電力・AI関連論文を取得
2. **関連度評価**: 電力分野への関連度をAIが自動評価
3. **要約生成**: 高関連度論文の日本語要約を生成
4. **データ保存**: SQLiteデータベースに履歴を保存
5. **メール送信**: 要約と全論文リストをGmail経由で配信

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

