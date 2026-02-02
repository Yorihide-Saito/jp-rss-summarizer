# jp-rss-summarizer

英語RSSフィードを自動取得し、GPT-4o-miniで日本語要約してRSS配信するツール。

## RSSフィード一覧

| カテゴリ | URL |
|---------|-----|
| arXiv（学術論文） | `https://yorihide-saito.github.io/jp-rss-summarizer/feed_arxiv.xml` |
| 科学 × ファッション | `https://yorihide-saito.github.io/jp-rss-summarizer/feed_1.xml` |
| 健康・最適化 | `https://yorihide-saito.github.io/jp-rss-summarizer/feed_2.xml` |
| 野心・戦略思考 | `https://yorihide-saito.github.io/jp-rss-summarizer/feed_3.xml` |
| AI・実装 | `https://yorihide-saito.github.io/jp-rss-summarizer/feed_4_ai.xml` |
| クリエイティブ・エンジニアリング | `https://yorihide-saito.github.io/jp-rss-summarizer/feed_5.xml` |

## セットアップ

### 1. OpenAI APIキーを Secrets に登録

1. リポジトリ → **Settings**
2. **Secrets and variables** → **Actions**
3. **New repository secret** をクリック
4. Name: `OPENAI_API_KEY`、Value: あなたのAPIキー

### 2. GitHub Pages を有効化

1. リポジトリ → **Settings**
2. **Pages**
3. **Build and deployment** の Source を **GitHub Actions** に変更

## 実行方法

### 手動実行（GitHub Actions）

1. リポジトリの **Actions** タブを開く
2. 左側の **build-jp-rss** を選択
3. **Run workflow** → **Run workflow** ボタンをクリック

### 自動実行

GitHub Actions により、毎日 UTC 0:00 / 12:00（日本時間 9:00 / 21:00）に自動実行されます。

### ローカル実行

```bash
# 依存関係インストール
pip install feedparser openai python-dotenv

# .env ファイルを作成
echo "OPENAI_API_KEY=your-api-key" > .env

# 実行
python summarize.py
```

## ファイル構成

```
jp-rss-summarizer/
├── summarize.py          # メインスクリプト
├── feeds.txt             # 監視するRSSフィード一覧
├── state.json            # 処理済み記事の管理
├── public/               # 生成されたRSSファイル
│   └── feed_*.xml
├── .github/workflows/
│   └── build.yml         # GitHub Actions 設定
└── .env                  # APIキー（.gitignoreで除外）
```

## カスタマイズ

### フィードの追加・削除

`feeds.txt` を編集してください。`# ===== カテゴリ名 =====` の形式でカテゴリを分けると、カテゴリごとに別々のRSSファイルが生成されます。

### 処理件数の調整

`summarize.py` の `MAX_ITEMS_PER_FEED` を変更してください（デフォルト: 5件/フィード）。
