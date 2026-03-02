# 機能設計書 - Nano Banana Pro Plugin

## 1. 文書情報

| 項目 | 内容 |
|------|------|
| 文書名 | 機能設計書 |
| プロジェクト名 | Nano Banana Pro Plugin |
| バージョン | 0.1.0 |
| 作成日 | 2025-02-14 |
| 作成者 | kuroneko4423 |

### 改訂履歴

| 版数 | 日付 | 改訂内容 | 担当者 |
|------|------|----------|--------|
| 0.0.1 | 2025-02-14 | 初版作成 | takumi |
| 0.1.0 | 2026-03-02 | Nano Banana 2 モデルサポート追加、model パラメータ追加、auto オプション追加、Flash 専用オプション追加 | kuroneko4423 |

---

## 2. 機能一覧

| 機能 ID | 機能名 | 概要 | 対応ファイル |
|---------|--------|------|-------------|
| F-001 | 認証検証機能 | Gemini API キーの有効性を検証 | `provider/nanobananapro.py` |
| F-002 | 画像生成機能 | テキストプロンプトから画像を生成 | `tools/generate_image.py` |
| F-003 | 画像編集機能 | 既存画像を自然言語指示で編集 | `tools/edit_image.py` |

---

## 3. F-001: 認証検証機能

### 3.1 機能概要

Dify プラグイン設定画面で入力された Gemini API キーの有効性を検証する。Gemini API の `models.list` エンドポイントに対して軽量なリクエストを送信し、認証の成否を判定する。

### 3.2 入力仕様

| パラメータ名 | 型 | 必須 | 説明 |
|-------------|-----|------|------|
| `gemini_api_key` | secret-input | 必須 | Google AI Studio で取得した Gemini API キー |

### 3.3 処理フロー

```
開始
  │
  ▼
API キーが空文字？ ──Yes──> ToolProviderCredentialValidationError 送出
  │                         "Gemini API Key is required."
  No
  │
  ▼
GET /v1beta/models?key={api_key}
(タイムアウト: 10 秒)
  │
  ├── ConnectionError ──> ToolProviderCredentialValidationError 送出
  │                       "Failed to connect to the Gemini API..."
  │
  ├── ステータス 401 or 403 ──> ToolProviderCredentialValidationError 送出
  │                              "Invalid Gemini API Key..."
  │
  ├── その他のHTTPエラー ──> raise_for_status() → 例外キャッチ
  │                          ToolProviderCredentialValidationError 送出
  │                          "Credential validation failed: {error}"
  │
  └── ステータス 200 ──> 正常終了（例外なし）
```

### 3.4 出力仕様

| 結果 | 動作 |
|------|------|
| 成功 | メソッドが正常に完了（例外なし） |
| 失敗 | `ToolProviderCredentialValidationError` 例外を送出 |

### 3.5 エラーケース

| エラー条件 | エラーメッセージ |
|-----------|----------------|
| API キー未入力（空文字） | `"Gemini API Key is required."` |
| 認証失敗（HTTP 401/403） | `"Invalid Gemini API Key. Please check your credentials."` |
| 接続エラー | `"Failed to connect to the Gemini API. Please check your network."` |
| その他の例外 | `"Credential validation failed: {エラー内容}"` |

---

## 4. F-002: 画像生成機能

### 4.1 機能概要

テキストプロンプトから **Nano Banana Pro（Gemini 3 Pro Image）** または **Nano Banana 2（Gemini 3.1 Flash Image）** モデルを使用して高品質な画像を生成する。モデル選択、アスペクト比、解像度、温度パラメータなどのカスタマイズが可能。

### 4.2 入力パラメータ一覧

| パラメータ名 | 型 | 必須 | デフォルト | 入力方式 | 説明 |
|-------------|-----|------|-----------|---------|------|
| `model` | select | 任意 | `"gemini-3-pro-image-preview"` | form | 使用するモデルの選択 |
| `prompt` | string | 必須 | - | llm | 生成する画像の説明テキスト |
| `system_prompt` | string | 任意 | `""` | form | モデル動作を制御するシステム指示 |
| `aspect_ratio` | select | 任意 | `"auto"` | form | 出力画像のアスペクト比 |
| `resolution` | select | 任意 | `"auto"` | form | 出力画像の解像度 |
| `temperature` | number | 任意 | `1.0` | form | ランダム性の制御（0.0〜2.0） |

#### モデルの選択肢

| 値 | ラベル（ja_JP） | 説明 |
|----|----------------|------|
| `gemini-3-pro-image-preview` | Nano Banana Pro（Gemini 3 Pro） | 高精度なテキストレンダリング、高品質画像（デフォルト） |
| `gemini-3.1-flash-image-preview` | Nano Banana 2（Gemini 3.1 Flash） | 高速・低コスト、追加のアスペクト比・解像度に対応 |

#### アスペクト比の選択肢

| 値 | ラベル（ja_JP） | 説明 | 対応モデル |
|----|----------------|------|-----------|
| `auto` | 自動 | API のデフォルトに任せる | 全モデル |
| `1:1` | 1:1（正方形） | 正方形 | 全モデル |
| `16:9` | 16:9（横長） | 横長ワイドスクリーン | 全モデル |
| `9:16` | 9:16（縦長） | 縦長（モバイル向け） | 全モデル |
| `4:3` | 4:3（標準） | 標準横長 | 全モデル |
| `3:4` | 3:4（縦長標準） | 標準縦長 | 全モデル |
| `2:3` | 2:3（縦長 - Flash 専用） | 縦長 | Flash 専用 |
| `3:2` | 3:2（横長 - Flash 専用） | 横長 | Flash 専用 |
| `4:5` | 4:5（縦長トール - Flash 専用） | 縦長トール | Flash 専用 |
| `5:4` | 5:4（横長ワイド - Flash 専用） | 横長ワイド | Flash 専用 |
| `1:4` | 1:4（超縦長 - Flash 専用） | 超縦長 | Flash 専用 |
| `4:1` | 4:1（超横長 - Flash 専用） | 超横長 | Flash 専用 |
| `1:8` | 1:8（極端縦長 - Flash 専用） | 極端縦長 | Flash 専用 |
| `8:1` | 8:1（極端横長 - Flash 専用） | 極端横長 | Flash 専用 |
| `21:9` | 21:9（シネマティック - Flash 専用） | シネマティック | Flash 専用 |

#### 解像度の選択肢

| 値 | ラベル | ピクセル数 | 対応モデル |
|----|-------|-----------|-----------|
| `auto` | 自動 | API のデフォルト | 全モデル |
| `0.5K` | 0.5K（512px - Flash 専用） | 512px | Flash 専用 |
| `1K` | 1K（1024px） | 1024px | 全モデル |
| `2K` | 2K（2048px） | 2048px | 全モデル |
| `4K` | 4K（4096px） | 4096px | 全モデル |

#### 入力方式の区分

| 入力方式 | 説明 |
|---------|------|
| `llm` | Dify の LLM がワークフロー内で自動的に値を決定 |
| `form` | ユーザーがフォーム UI で直接入力 |

### 4.3 処理フロー

```
開始
  │
  ▼
1. パラメータ抽出
   model, prompt, aspect_ratio, resolution, temperature, system_prompt
  │
  ▼
2. API キー取得（runtime.credentials）
   API キーが空？ ──Yes──> yield "Error: Gemini API Key is not configured." → 終了
  │
  No
  │
  ▼
3. リクエストペイロード構築
   - contents[0].parts[0].text = prompt
   - generationConfig.responseModalities = ["TEXT", "IMAGE"]
   - generationConfig.temperature = temperature
   - aspect_ratio が "auto" でなければ imageConfig.aspectRatio を設定
   - resolution が "auto" でなければ imageConfig.imageSize を設定
   - imageConfig が空でなければ generationConfig.imageConfig に追加
   - system_prompt が空でなければ systemInstruction を追加
  │
  ▼
4. POST /v1beta/models/{model_id}:generateContent
   (model_id は model パラメータから取得。デフォルト: gemini-3-pro-image-preview)
   (タイムアウト: 120 秒)
  │
  ├── Timeout ──> yield "Error: Request timed out..." → 終了
  ├── ConnectionError ──> yield "Error: Failed to connect..." → 終了
  ├── その他例外 ──> yield "Error: {内容}" → 終了
  ├── ステータス != 200 ──> yield "Gemini API error ({code}): {detail}" → 終了
  │
  └── ステータス 200
      │
      ▼
5. レスポンスパース
   candidates が空？
   ├── Yes → blockReason あり？
   │         ├── Yes → yield "Image generation was blocked..." → 終了
   │         └── No  → yield "No image was generated..." → 終了
   └── No
       │
       ▼
6. candidates[0].content.parts をループ
   各 part に対して:
   ├── "text" あり → yield create_text_message(part["text"])
   └── "inlineData" あり → Base64 デコード → yield create_blob_message(画像バイト)
  │
  ▼
7. 画像パートが見つからなかった場合
   yield "The model returned a response but no image was generated..."
  │
  ▼
終了
```

### 4.4 出力仕様

| 出力タイプ | 形式 | 説明 |
|-----------|------|------|
| Blob メッセージ | `ToolInvokeMessage` (blob) | 生成された画像データ（MIME タイプ付き） |
| テキストメッセージ | `ToolInvokeMessage` (text) | モデルが返した説明テキスト |

### 4.5 エラーケース

| エラー条件 | ユーザーメッセージ |
|-----------|------------------|
| API キー未設定 | `"Error: Gemini API Key is not configured."` |
| API エラー（非 200） | `"Gemini API error ({status_code}): {error_detail}"` |
| タイムアウト（120 秒超） | `"Error: Request timed out. Image generation may take up to 2 minutes. Please try again or use a lower resolution."` |
| 接続エラー | `"Error: Failed to connect to the Gemini API."` |
| その他の例外 | `"Error: {例外メッセージ}"` |
| 安全性ブロック | `"Image generation was blocked. Reason: {blockReason}. Please modify your prompt and try again."` |
| 候補なし（ブロック理由なし） | `"No image was generated. Please try a different prompt."` |
| 画像パートなし | `"The model returned a response but no image was generated. Try rephrasing your prompt to focus on visual content."` |

---

## 5. F-003: 画像編集機能

### 5.1 機能概要

既存の画像に対して、自然言語の指示に基づいた編集を行う。入力画像と編集指示テキストを Gemini API に送信し、編集済み画像を取得する。

対応する編集操作の例：
- スタイル変更（画風変換）
- オブジェクトの追加・削除
- 色調調整
- テキストオーバーレイ
- 背景変更
- インペインティング

### 5.2 入力パラメータ一覧

| パラメータ名 | 型 | 必須 | デフォルト | 入力方式 | 説明 |
|-------------|-----|------|-----------|---------|------|
| `model` | select | 任意 | `"gemini-3-pro-image-preview"` | form | 使用するモデルの選択 |
| `prompt` | string | 必須 | - | llm | 編集指示テキスト |
| `image` | file | 必須 | - | llm | 編集対象の入力画像 |
| `system_prompt` | string | 任意 | `""` | form | モデル動作を制御するシステム指示 |
| `aspect_ratio` | select | 任意 | `"auto"` | form | 出力画像のアスペクト比 |
| `resolution` | select | 任意 | `"auto"` | form | 出力画像の解像度 |

> **注記**: 画像生成機能（F-002）と異なり、`temperature` パラメータは画像編集機能では使用しない。

### 5.3 対応画像フォーマット

| 拡張子 | MIME タイプ |
|--------|-----------|
| `.jpg` / `.jpeg` | `image/jpeg` |
| `.png` | `image/png` |
| `.webp` | `image/webp` |
| `.heic` | `image/heic` |
| `.heif` | `image/heif` |

### 5.4 処理フロー

```
開始
  │
  ▼
1. パラメータ抽出
   model, prompt, image_file, aspect_ratio, resolution, system_prompt
  │
  ▼
2. 入力画像の検証
   image_file が空？ ──Yes──> yield "Error: An input image is required..." → 終了
  │
  No
  │
  ▼
3. API キー取得（runtime.credentials）
   API キーが空？ ──Yes──> yield "Error: Gemini API Key is not configured." → 終了
  │
  No
  │
  ▼
4. 画像読み込み (_read_image)
   ├── 例外発生 → yield "Error reading image: {内容}" → 終了
   ├── 戻り値 None → yield "Error: Failed to read the input image." → 終了
   └── 成功 → image_data = {bytes, mime_type}
  │
  ▼
5. Base64 エンコード
   image_b64 = base64.b64encode(image_data["bytes"])
  │
  ▼
6. リクエストペイロード構築
   - contents[0].parts[0].text = prompt
   - contents[0].parts[1].inlineData = {mimeType, data: image_b64}
   - generationConfig.responseModalities = ["TEXT", "IMAGE"]
   - aspect_ratio が "auto" でなければ imageConfig.aspectRatio を設定
   - resolution が "auto" でなければ imageConfig.imageSize を設定
   - imageConfig が空でなければ generationConfig.imageConfig に追加
   - system_prompt が空でなければ systemInstruction を追加
  │
  ▼
7. POST /v1beta/models/{model_id}:generateContent
   (model_id は model パラメータから取得。デフォルト: gemini-3-pro-image-preview)
   (タイムアウト: 120 秒)
   ※ 画像生成機能と同様のエラーハンドリング
  │
  ▼
8. レスポンスパース
   ※ 画像生成機能と同様の処理
  │
  ▼
終了
```

### 5.5 出力仕様

画像生成機能（F-002）と同一。Blob メッセージ（編集済み画像）とテキストメッセージを返却する。

### 5.6 エラーケース

画像生成機能（F-002）のエラーケースに加え、以下の画像編集固有のエラーが存在する：

| エラー条件 | ユーザーメッセージ |
|-----------|------------------|
| 入力画像未指定 | `"Error: An input image is required for editing."` |
| 画像読み込み失敗（_read_image が None を返却） | `"Error: Failed to read the input image."` |
| 画像読み込みエラー（例外発生） | `"Error reading image: {例外メッセージ}"` |
| 安全性ブロック | `"Image editing was blocked. Reason: {blockReason}. Please modify your instructions and try again."` |
| 候補なし（ブロック理由なし） | `"No edited image was generated. Please try different instructions."` |
| 画像パートなし | `"The model returned a response but no edited image was generated. Try rephrasing your edit instructions."` |

---

## 6. 機能間の共通事項

### 6.1 共通エラーハンドリングパターン

画像生成機能（F-002）と画像編集機能（F-003）は以下のエラーハンドリングを共有する：

1. API キー未設定チェック
2. `requests.Timeout` 例外のキャッチ
3. `requests.ConnectionError` 例外のキャッチ
4. 汎用 `Exception` のキャッチ
5. HTTP ステータスコードによるエラー判定
6. `candidates` 空時の安全性ブロックチェック
7. `_extract_error` メソッドによるエラーメッセージ抽出

### 6.2 出力メッセージの種類

| メッセージ種別 | 生成方法 | 用途 |
|-------------|---------|------|
| テキストメッセージ | `create_text_message(text)` | エラー通知、モデルの説明テキスト |
| Blob メッセージ | `create_blob_message(blob, meta)` | 画像データの返却（MIME タイプ付き） |
