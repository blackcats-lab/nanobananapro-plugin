# Nano Banana Pro - Dify Plugin

Google Gemini API の **Nano Banana Pro**（Gemini 3 Pro Image / `gemini-3-pro-image-preview`）を Dify から利用するためのプラグインです。

## 機能

### 🎨 画像生成（Generate Image）
テキストプロンプトから高品質な画像を生成します。

- 最大 **4K** 解像度出力（1K / 2K / 4K）
- 複数のアスペクト比（1:1, 16:9, 9:16, 4:3, 3:4）
- 高精度なテキストレンダリング（多言語対応）
- Thinking モードによる複雑な構図の推論

### ✏️ 画像編集（Edit Image）
自然言語の指示で既存画像を編集します。

- スタイル変更
- オブジェクトの追加・削除
- 色調調整
- テキストオーバーレイ
- 背景変更

## セットアップ

### 1. Gemini API キーの取得

[Google AI Studio](https://aistudio.google.com/app/apikey) から API キーを取得してください。

### 2. プラグインのインストール

`.difypkg` ファイルを Dify のプラグイン管理画面からアップロードしてインストールします。

### 3. 認証情報の設定

インストール後、プラグイン設定画面で Gemini API キーを入力してください。

## 開発・デバッグ

### 環境要件

- Python ≥ 3.12
- Dify Plugin CLI

### Dify Plugin CLI のインストール

**Mac:**

```bash
brew tap langgenius/dify
brew install dify
```

**Linux / Windows:**

[GitHub Releases](https://github.com/langgenius/dify-plugin-daemon/releases) からバイナリをダウンロードし、パスの通ったディレクトリに配置してください。

```bash
dify version  # インストール確認
```

### ローカルで実行

```bash
# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt

# .env ファイルの設定
cp .env.example .env
# .env を編集してデバッグキー等を設定

# プラグインの起動
python -m main
```

### パッケージング

```bash
# プラグインの親ディレクトリで実行
dify plugin package ./nanobananapro-plugin
```

### 署名について

プラグインのアップロード時に署名検証エラーが発生する場合：

**方法1: 署名検証を無効化する（開発環境向け）**

Dify の Plugin Daemon の `.env` に以下を設定し、コンテナを再起動してください。

```
FORCE_VERIFYING_SIGNATURE=false
```

**方法2: プラグインに署名する**

```bash
# 鍵ペアの生成
dify signature generate -f my_key

# パッケージに署名
dify signature sign nanobananapro-plugin.difypkg -p my_key.private.pem

# 署名の検証（確認用）
dify signature verify nanobananapro-plugin.signed.difypkg -p my_key.public.pem
```

署名後、公開鍵（`.public.pem`）を Dify 管理者に渡し、Plugin Daemon に登録してもらってください。

## トラブルシューティング

### 署名検証エラー

```
PluginDaemonBadRequestError: plugin verification has been enabled, and the plugin you want to install has a bad signature
```

上記「署名について」セクションを参照してください。

### プラグイン起動時に FileNotFoundError

```
FileNotFoundError: [Errno 2] No such file or directory: '.../<name>.py'
```

各 YAML ファイルの `extra.python.source` がプラグインルートからの相対パスになっているか確認してください。

```yaml
# NG
extra:
  python:
    source: nanobananapro.py

# OK
extra:
  python:
    source: provider/nanobananapro.py
```

### maximum recursion depth exceeded

```
ValueError: Error loading plugin configuration: Failed to load YAML file manifest.yaml: maximum recursion depth exceeded
```

エントリーポイントのファイル名（`manifest.yaml` の `entrypoint`）と、プロバイダー/ツールの `extra.python.source` で指定するファイル名が衝突すると再帰ロードが発生します。エントリーポイントは `main.py` のままにし、`source` パスにはディレクトリを含めてください（例: `provider/nanobananapro.py`）。

### パッケージサイズ超過

```
ERROR failed to package plugin error="Plugin package size is too large."
```

`.difyignore` に `venv/` や不要なファイルを追加してください。

```
venv/
__pycache__/
*.pyc
*.difypkg
.env
```

## ディレクトリ構造

```
nanobananapro-plugin/
├── _assets/
│   └── icon.svg                 # プラグインアイコン
├── provider/
│   ├── nanobananapro.yaml       # プロバイダー定義
│   └── nanobananapro.py         # 認証検証コード
├── tools/
│   ├── generate_image.yaml      # 画像生成ツール定義
│   ├── generate_image.py        # 画像生成実装
│   ├── edit_image.yaml          # 画像編集ツール定義
│   └── edit_image.py            # 画像編集実装
├── main.py                      # エントリーポイント
├── manifest.yaml                # プラグイン設定
├── requirements.txt             # Python 依存パッケージ
├── .env.example                 # デバッグ設定テンプレート
├── .difyignore                  # パッケージング除外設定
└── README.md
```

## モデルについて

**Nano Banana Pro**（`gemini-3-pro-image-preview`）は Google DeepMind が開発した画像生成・編集モデルです。

- Gemini 3 Pro の高度な推論能力を活用
- テキストレンダリングの精度が非常に高い
- 最大 14 枚の参照画像をサポート
- 最大 5 人の人物の一貫性を維持
- SynthID ウォーターマーク付き

## ライセンス

MIT License

## 作者

blackcats-lab
