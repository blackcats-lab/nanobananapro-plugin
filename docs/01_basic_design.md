# 基本設計書 - Nano Banana Pro Plugin

## 1. 文書情報

| 項目 | 内容 |
|------|------|
| 文書名 | 基本設計書 |
| プロジェクト名 | Nano Banana Pro Plugin |
| バージョン | 0.0.1 |
| 作成日 | 2025-02-14 |
| 作成者 | takumi |

### 改訂履歴

| 版数 | 日付 | 改訂内容 | 担当者 |
|------|------|----------|--------|
| 0.0.1 | 2025-02-14 | 初版作成 | takumi |

---

## 2. システム概要

### 2.1 プラグインの目的

Nano Banana Pro Plugin は、Dify プラットフォーム上で Google の Nano Banana Pro（Gemini 3 Pro Image）モデルを利用した画像生成・編集機能を提供する Dify プラグインである。

本プラグインにより、Dify ユーザーはワークフロー内で以下の操作を実行できる：

- **テキストからの画像生成** - テキストプロンプトによる高品質画像の生成（最大 4K 解像度）
- **自然言語による画像編集** - 既存画像に対する自然言語指示での編集（スタイル変更、オブジェクト追加・削除等）

### 2.2 対象ユーザー

- Dify プラットフォーム利用者（ワークフロー構築者、AI アプリ開発者）
- Dify プラグインを通じて画像生成・編集を組み込みたい開発者

### 2.3 システム名称

| 名称 | 説明 |
|------|------|
| Nano Banana Pro | プラグインの表示名 |
| nanobananapro | プラグインの内部名（manifest.yaml） |
| gemini-3-pro-image-preview | 利用する Gemini モデル ID |

---

## 3. システム構成図

### 3.1 全体アーキテクチャ図

```
┌──────────────────────────────────────────────────────────────────┐
│                      Dify Platform                               │
│                                                                  │
│  ┌────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  ユーザー   │───>│  Dify Workflow    │───>│  Plugin Runtime  │  │
│  │  (UI/API)  │<───│  Engine           │<───│                  │  │
│  └────────────┘    └──────────────────┘    └────────┬─────────┘  │
│                                                      │           │
└──────────────────────────────────────────────────────┼───────────┘
                                                       │
                                          ┌────────────▼───────────┐
                                          │  Nano Banana Pro       │
                                          │  Plugin                │
                                          │                        │
                                          │  ┌──────────────────┐  │
                                          │  │ Provider         │  │
                                          │  │ (認証検証)        │  │
                                          │  └──────────────────┘  │
                                          │  ┌──────────────────┐  │
                                          │  │ GenerateImageTool│  │
                                          │  │ (画像生成)        │  │
                                          │  └──────────────────┘  │
                                          │  ┌──────────────────┐  │
                                          │  │ EditImageTool    │  │
                                          │  │ (画像編集)        │  │
                                          │  └──────────────────┘  │
                                          └────────────┬───────────┘
                                                       │
                                                       │ HTTPS
                                                       ▼
                                          ┌────────────────────────┐
                                          │  Google Gemini API     │
                                          │  (v1beta)              │
                                          │                        │
                                          │  Model:                │
                                          │  gemini-3-pro-image-   │
                                          │  preview               │
                                          └────────────────────────┘
```

### 3.2 ディレクトリ構成

```
nanobananapro-plugin/
├── _assets/
│   └── icon.svg                  # プラグインアイコン
├── provider/
│   ├── __init__.py               # モジュール初期化
│   ├── nanobananapro.yaml        # プロバイダ設定（認証情報スキーマ）
│   └── nanobananapro.py          # 認証検証ロジック
├── tools/
│   ├── __init__.py               # モジュール初期化
│   ├── generate_image.yaml       # 画像生成ツール定義
│   ├── generate_image.py         # 画像生成ロジック
│   ├── edit_image.yaml           # 画像編集ツール定義
│   └── edit_image.py             # 画像編集ロジック
├── main.py                       # エントリーポイント
├── manifest.yaml                 # プラグインメタデータ
├── requirements.txt              # Python 依存ライブラリ
├── .env.example                  # 環境変数テンプレート
├── .difyignore                   # パッケージ除外設定
├── .gitignore                    # Git 除外設定
└── README.md                     # プロジェクト説明
```

### 3.3 コンポーネント一覧

| コンポーネント名 | ファイル | クラス名 | 役割 |
|-----------------|---------|---------|------|
| エントリーポイント | `main.py` | - | Plugin インスタンス生成・起動 |
| 認証プロバイダ | `provider/nanobananapro.py` | `NanoBananaProProvider` | Gemini API キーの検証 |
| 画像生成ツール | `tools/generate_image.py` | `GenerateImageTool` | テキストから画像を生成 |
| 画像編集ツール | `tools/edit_image.py` | `EditImageTool` | 既存画像を自然言語で編集 |

---

## 4. データフロー図

### 4.1 画像生成フロー

```
ユーザー入力                  Plugin                          Gemini API
    │                          │                                │
    │  prompt, aspect_ratio,   │                                │
    │  resolution, temperature │                                │
    │─────────────────────────>│                                │
    │                          │  POST /generateContent         │
    │                          │  (JSON: text + config)         │
    │                          │───────────────────────────────>│
    │                          │                                │
    │                          │  200 OK                        │
    │                          │  (candidates[].parts[]:        │
    │                          │   text + inlineData/base64)    │
    │                          │<───────────────────────────────│
    │                          │                                │
    │  ToolInvokeMessage       │                                │
    │  (Blob: 画像データ)       │                                │
    │  (Text: 説明テキスト)     │                                │
    │<─────────────────────────│                                │
```

### 4.2 画像編集フロー

```
ユーザー入力                  Plugin                          Gemini API
    │                          │                                │
    │  prompt, image,          │                                │
    │  aspect_ratio, resolution│                                │
    │─────────────────────────>│                                │
    │                          │ _read_image()                  │
    │                          │ → Base64エンコード              │
    │                          │                                │
    │                          │  POST /generateContent         │
    │                          │  (JSON: text + inlineData      │
    │                          │   + config)                    │
    │                          │───────────────────────────────>│
    │                          │                                │
    │                          │  200 OK                        │
    │                          │  (candidates[].parts[]:        │
    │                          │   text + inlineData/base64)    │
    │                          │<───────────────────────────────│
    │                          │                                │
    │  ToolInvokeMessage       │                                │
    │  (Blob: 編集済み画像)     │                                │
    │<─────────────────────────│                                │
```

### 4.3 認証検証フロー

```
Dify 管理画面               Provider                        Gemini API
    │                          │                                │
    │  gemini_api_key          │                                │
    │─────────────────────────>│                                │
    │                          │  GET /models?key=xxx           │
    │                          │───────────────────────────────>│
    │                          │                                │
    │                          │  200 OK / 401 / 403            │
    │                          │<───────────────────────────────│
    │                          │                                │
    │  成功 or エラーメッセージ  │                                │
    │<─────────────────────────│                                │
```

---

## 5. 技術スタック

| カテゴリ | 技術 | バージョン |
|---------|------|-----------|
| 言語 | Python | 3.12 |
| フレームワーク | Dify Plugin SDK | `dify_plugin` |
| HTTP クライアント | requests | >= 2.31.0 |
| 外部 API | Google Gemini API | v1beta |
| モデル | gemini-3-pro-image-preview | - |

---

## 6. 動作環境・制約

### 6.1 リソース制限

| リソース | 制限値 | 備考 |
|---------|-------|------|
| メモリ | 256 MB (268,435,456 bytes) | manifest.yaml で定義 |
| ストレージ | 1 MB (1,048,576 bytes) | プラグインストレージ上限 |
| リクエストタイムアウト | 120 秒 | MAX_REQUEST_TIMEOUT |

### 6.2 パーミッション

| パーミッション | 状態 |
|--------------|------|
| tool | 有効 |
| model (llm, text_embedding, rerank, tts, speech2text, moderation) | 無効 |
| node | 無効 |
| endpoint | 無効 |
| app | 無効 |
| storage | 有効（1 MB） |
| verify | 無効 |

### 6.3 対応アーキテクチャ

- amd64
- arm64

### 6.4 多言語対応

| 言語コード | 言語 |
|-----------|------|
| en_US | 英語 |
| ja_JP | 日本語 |
| zh_Hans | 簡体字中国語 |

---

## 7. 外部インターフェース概要

### 7.1 Gemini API

| 項目 | 値 |
|------|-----|
| ベース URL | `https://generativelanguage.googleapis.com/v1beta` |
| 認証方式 | API キー（URL クエリパラメータ `key`） |
| モデル | `gemini-3-pro-image-preview` |
| プロトコル | HTTPS |

### 7.2 Dify Plugin インターフェース

| 基底クラス | 提供元 | 用途 |
|-----------|--------|------|
| `ToolProvider` | dify_plugin | 認証情報の検証 |
| `Tool` | dify_plugin | ツール処理の実装 |
| `ToolInvokeMessage` | dify_plugin.entities.tool | レスポンスメッセージ |
| `ToolProviderCredentialValidationError` | dify_plugin.errors.tool | 認証エラー |

---

## 8. 非機能要件

### 8.1 性能

| 項目 | 要件 |
|------|------|
| 画像生成応答時間 | 120 秒以内 |
| 認証検証応答時間 | 10 秒以内 |
| 画像解像度 | 最大 4K（4096px） |

### 8.2 信頼性

- Gemini API のタイムアウト、接続エラー、API エラーに対する包括的なエラーハンドリング
- 安全性ブロック（blockReason）の検出とユーザーへの通知
- ジェネレータパターンによるストリーミングレスポンス

### 8.3 セキュリティ

- API キーは Dify の `secret-input` 型で暗号化保管
- API キーはエラーメッセージに含めない設計
- HTTPS 通信のみ使用
- Gemini API 側の安全性フィルタによるコンテンツフィルタリング
- SynthID ウォーターマークによる生成画像の識別

### 8.4 保守性

- Provider / Tool の分離によるモジュール構成
- YAML ベースの宣言的なツール定義
- ソースコード約 450 行の小規模構成
