# API 設計書 - Nano Banana Pro Plugin

## 1. 文書情報

| 項目 | 内容 |
|------|------|
| 文書名 | API 設計書 |
| プロジェクト名 | Nano Banana Pro Plugin |
| バージョン | 0.0.1 |
| 作成日 | 2025-02-14 |
| 作成者 | takumi |

### 改訂履歴

| 版数 | 日付 | 改訂内容 | 担当者 |
|------|------|----------|--------|
| 0.0.1 | 2025-02-14 | 初版作成 | takumi |

---

## 2. API 概要

### 2.1 利用 API

| 項目 | 値 |
|------|-----|
| API 名 | Google Gemini API |
| API バージョン | v1beta |
| ベース URL | `https://generativelanguage.googleapis.com/v1beta` |
| 対象モデル | `gemini-3-pro-image-preview` |

### 2.2 認証方式

| 項目 | 値 |
|------|-----|
| 認証方式 | API キー |
| 送信方法 | URL クエリパラメータ（`key`） |
| 取得先 | [Google AI Studio](https://aistudio.google.com/app/apikey) |

---

## 3. エンドポイント一覧

| # | メソッド | エンドポイント | 用途 | 使用箇所 |
|---|---------|---------------|------|---------|
| API-001 | GET | `/v1beta/models` | モデル一覧取得（認証検証用） | `NanoBananaProProvider` |
| API-002 | POST | `/v1beta/models/gemini-3-pro-image-preview:generateContent` | 画像生成・画像編集 | `GenerateImageTool`, `EditImageTool` |

---

## 4. API-001: モデル一覧取得（認証検証）

### 4.1 リクエスト仕様

| 項目 | 値 |
|------|-----|
| メソッド | GET |
| URL | `{BASE_URL}/models?key={api_key}` |
| ヘッダー | なし |
| ボディ | なし |
| タイムアウト | 10 秒 |

### 4.2 リクエスト例

```
GET https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSy...
```

### 4.3 レスポンス（正常時）

| 項目 | 値 |
|------|-----|
| ステータス | 200 OK |
| ボディ | モデル一覧 JSON |

> **注記**: 本プラグインではレスポンスボディの内容は使用しない。ステータスコードのみで認証の成否を判定する。

### 4.4 レスポンス（異常時）

| ステータス | 意味 | プラグイン側の処理 |
|-----------|------|-----------------|
| 401 | 未認証 | `ToolProviderCredentialValidationError` 送出 |
| 403 | 禁止 | `ToolProviderCredentialValidationError` 送出 |
| その他 | 各種エラー | `raise_for_status()` → 汎用例外ハンドラで処理 |

---

## 5. API-002: 画像生成・編集（generateContent）

### 5.1 リクエスト仕様

| 項目 | 値 |
|------|-----|
| メソッド | POST |
| URL | `{BASE_URL}/models/gemini-3-pro-image-preview:generateContent?key={api_key}` |
| Content-Type | `application/json` |
| タイムアウト | 120 秒 |

### 5.2 リクエストボディ（画像生成）

```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "A beautiful sunset over the ocean with vibrant orange and purple colors"
        }
      ]
    }
  ],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "temperature": 1.0,
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    }
  },
  "systemInstruction": {
    "parts": [
      {
        "text": "You are a professional photographer. Generate photorealistic images."
      }
    ]
  }
}
```

> **注記**: `systemInstruction` は `system_prompt` が空でない場合のみ含まれる。

### 5.3 リクエストボディ（画像編集）

```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "Change the background to a beach scene"
        },
        {
          "inlineData": {
            "mimeType": "image/png",
            "data": "iVBORw0KGgoAAAANSUhEUgAA..."
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "imageConfig": {
      "aspectRatio": "1:1",
      "imageSize": "1K"
    }
  }
}
```

> **注記**: 画像編集時のリクエストには `temperature` フィールドを含まない。

### 5.4 画像生成と画像編集のリクエスト差分

| フィールド | 画像生成 | 画像編集 |
|-----------|---------|---------|
| `contents[0].parts` | `[{text}]` | `[{text}, {inlineData}]` |
| `generationConfig.temperature` | あり（0.0〜2.0） | なし |
| `inlineData` | なし | 入力画像の Base64 エンコードデータ |

### 5.5 レスポンス（正常時 - 画像あり）

```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "Here is the generated image of a sunset over the ocean."
          },
          {
            "inlineData": {
              "mimeType": "image/png",
              "data": "iVBORw0KGgoAAAANSUhEUgAA..."
            }
          }
        ]
      }
    }
  ]
}
```

**レスポンスの処理**:

| パート種別 | 判定条件 | プラグイン側の処理 |
|-----------|---------|-----------------|
| テキスト | `"text" in part` | `create_text_message(part["text"])` |
| 画像 | `"inlineData" in part` | Base64 デコード → `create_blob_message(bytes, {mime_type})` |

### 5.6 レスポンス（安全性ブロック時）

```json
{
  "promptFeedback": {
    "blockReason": "SAFETY"
  }
}
```

> `candidates` が空かつ `promptFeedback.blockReason` が存在する場合、安全性によるブロックとして処理する。

### 5.7 レスポンス（API エラー時）

```json
{
  "error": {
    "message": "Request payload size exceeds the limit: 20971520 bytes.",
    "code": 400
  }
}
```

**エラーメッセージ抽出ロジック**:

```
1. response.json() で JSON パースを試行
2. error.message が存在すればその値を返却
3. message がなければ response.text の先頭 500 文字を返却
4. JSON パース失敗時も response.text の先頭 500 文字を返却
```

---

## 6. パラメータ仕様

### 6.1 responseModalities

| 値 | 説明 |
|----|------|
| `"TEXT"` | テキスト形式のレスポンスを要求 |
| `"IMAGE"` | 画像形式のレスポンスを要求 |

本プラグインでは常に `["TEXT", "IMAGE"]` を指定し、テキストと画像の両方を返却させる。

### 6.2 aspectRatio

| 値 | 説明 | 用途例 |
|----|------|-------|
| `"1:1"` | 正方形 | プロフィール画像、サムネイル |
| `"16:9"` | 横長ワイドスクリーン | プレゼン資料、バナー |
| `"9:16"` | 縦長 | スマートフォン壁紙、ストーリー |
| `"4:3"` | 標準横長 | 一般的な写真比率 |
| `"3:4"` | 標準縦長 | ポートレート写真 |

### 6.3 imageSize

| 値 | ピクセル数 | 用途 |
|----|-----------|------|
| `"1K"` | 1024px | プレビュー、Web 表示向け |
| `"2K"` | 2048px | 高品質表示 |
| `"4K"` | 4096px | 印刷品質、プロフェッショナル用途 |

> 高解像度ほど処理時間とコストが増加する。

### 6.4 temperature

| 項目 | 値 |
|------|-----|
| 型 | number |
| 範囲 | 0.0 〜 2.0 |
| デフォルト | 1.0 |
| 用途 | 出力のランダム性制御 |

| 値の傾向 | 説明 |
|---------|------|
| 0.0 に近い | より決定的・一貫した結果 |
| 2.0 に近い | よりランダム・多様な結果 |

---

## 7. HTTP ステータスコード対応表

| ステータス | 意味 | プラグイン側の処理 |
|-----------|------|-----------------|
| 200 | 成功 | レスポンスパース処理へ進む |
| 400 | 不正リクエスト | `_extract_error` でメッセージ抽出 → テキストメッセージとして返却 |
| 401 | 未認証 | 認証検証時: `ToolProviderCredentialValidationError` 送出 / ツール実行時: エラーメッセージ返却 |
| 403 | 禁止 | 401 と同様の処理 |
| 429 | レート制限超過 | `_extract_error` でメッセージ抽出 → テキストメッセージとして返却 |
| 500 | サーバーエラー | `_extract_error` でメッセージ抽出 → テキストメッセージとして返却 |

---

## 8. 通信仕様

### 8.1 プロトコル

| 項目 | 値 |
|------|-----|
| プロトコル | HTTPS |
| TLS | Google API のデフォルト設定に準拠 |

### 8.2 認証情報の送信

API キーは URL クエリパラメータとして送信する（Gemini API の仕様に準拠）。

```
?key={gemini_api_key}
```

### 8.3 リクエストサイズ

画像データは Base64 エンコードして JSON ボディに含めるため、元画像の約 1.37 倍のサイズとなる。Gemini API 側のペイロード上限に注意が必要。

### 8.4 タイムアウト設定

| 用途 | タイムアウト値 | 設定箇所 |
|------|-------------|---------|
| 認証検証 | 10 秒 | `provider/nanobananapro.py` L29 |
| 画像生成 | 120 秒 | `tools/generate_image.py` L72 |
| 画像編集 | 120 秒 | `tools/edit_image.py` L104 |
| グローバル | 120 秒 | `main.py` L4 (`MAX_REQUEST_TIMEOUT`) |

---

## 9. セキュリティ考慮事項

### 9.1 API キー管理

| 項目 | 対策 |
|------|------|
| 保管方法 | Dify の `secret-input` 型による暗号化保管 |
| 送信方法 | HTTPS + URL クエリパラメータ |
| ログ出力 | エラーメッセージに API キーを含めない設計 |
| 環境変数 | `.env` ファイルは `.gitignore` と `.difyignore` で除外 |

### 9.2 通信セキュリティ

- 全通信は HTTPS で暗号化
- API エンドポイントは Google 管理のインフラ上で稼働
- `requests` ライブラリのデフォルト TLS 設定を使用

### 9.3 コンテンツ安全性

| 項目 | 説明 |
|------|------|
| 安全性フィルタ | Gemini API 側で自動的にコンテンツフィルタリングを実施 |
| ブロック検知 | `promptFeedback.blockReason` の存在をチェック |
| ユーザー通知 | ブロック理由をテキストメッセージとしてユーザーに返却 |
| ウォーターマーク | SynthID による生成画像の識別（Gemini API 側で自動付与） |
