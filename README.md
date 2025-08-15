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
DAYS_BACK=7
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

#### パフォーマンス調整
- `MAX_PAPERS`: 最終要約論文数（10-30推奨）
- `DAYS_BACK`: 検索期間（3-7日推奨）
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
システムは6段階の多段階フィルタリングパイプラインで動作します：

```
[大量論文収集] → [重複除去] → [日付フィルタ] → [関連度評価] → [複合スコア算出] → [バランス選択] → [要約生成] → [データ保存] → [メール送信]
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

### 🎯 Step 2-6: 多段階フィルタリングシステム
**担当モジュール**: `paper_fetcher.py` - `_apply_multi_stage_filtering()`

#### Stage 1: 全論文収集
- 各キーワードから取得した論文を統合
- 合計200+件の論文プールを構築

#### Stage 2: 重複除去
- 論文IDベースの重複検出
- ユニークな論文のみを保持

#### Stage 3: 日付フィルタ
- 過去`DAYS_BACK`日以内の論文に絞り込み
- 古い論文を除外して処理効率を向上

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

### 🤖 Step 7: AI要約生成  
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

### 💾 Step 8: データベース保存
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
       importance_score REAL,        -- 新規追加
       relevance_score REAL,         -- 新規追加
       combined_score REAL,          -- 新規追加
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **保存処理**
   - 論文IDによる重複チェック
   - 重要度・関連度・複合スコアの保存
   - トランザクション処理で一括保存
   - エラー時の自動ロールバック

### 📧 Step 9: メール配信
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
# 多段階フィルタリング段階
初期検索で200件の論文を収集します...
Stage 1: 全245件の論文を収集
Stage 2: 重複除去後198件
Stage 3: 日付フィルタ後156件
Stage 4: 関連度フィルタ後78件
Stage 5: 複合スコアフィルタ後45件
Stage 6: 最終選択30件

# スコア分布統計
選択論文スコア分布: 関連度平均72.3(最高95.2), 重要度平均64.1(最高88.7), 高関連度論文18件

# 要約処理段階
論文要約中 1/30 (重要度:88.7, 関連度:95.2): Advanced AI-Based Wind Power Forecasting...
論文要約中 2/30 (重要度:84.3, 関連度:87.9): Deep Learning for Solar Energy Prediction...

# 実行終了時
=== 処理完了 ===
発見論文総数: 245件
要約済み論文: 30件  
成功した要約: 28件
```

### ⚙️ 設定による動作調整

| 設定項目 | 影響する処理 | 推奨値 | 新機能での効果 |
|---------|-------------|--------|---------------|
| `SEARCH_KEYWORDS` | Stage1の初期検索範囲 | 幅広いキーワード | 大量収集戦略で検索範囲拡大 |
| `USER_KEYWORDS` | Stage4-6の関連度評価 | 特化したキーワード | バランス選択とフィルタリング |
| `DAYS_BACK` | Stage3の日付フィルタ | 3-7日 | 効率的な期間絞り込み |
| `MAX_PAPERS` | Stage6の最終選択数 | 10-30件 | 多段階フィルタ後の出力数 |
| OpenAI APIキー | Step7の要約品質 | 有効なキー | 重要度ベース適応的要約 |

### 🚀 システムの革新ポイント

#### 1. **検索戦略の革新**
- **従来**: 各キーワード10-20件 → **現在**: 各キーワード最大100件
- **効果**: 関連度の高い論文を見逃すリスクを大幅削減

#### 2. **多段階フィルタリング**
- **6段階のインテリジェントな絞り込み**
- **Stage 4-5**: 関連度・重要度・新しさの複合評価
- **Stage 6**: キーワードバランスを考慮した最終選択

#### 3. **高精度スコアリング**
- **関連度スコア**: 6要素による包括的評価
- **重要度スコア**: 電力分野特化の評価指標
- **複合スコア**: 3つの要素のバランス調整

#### 4. **効率的な処理**
- **大量収集 → 段階的絞り込み** で高品質論文を確実に発見
- **USER_KEYWORDS**による効率的なバランス選択
- **重要度ベース**の要約処理順序

この革新的な多段階フィルタリングシステムにより、電力・エネルギー分野に特化した高品質な論文要約システムを実現しています。

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

