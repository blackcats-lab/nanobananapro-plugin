# テスト設計書 - Nano Banana Pro Plugin

## 1. 文書情報

| 項目 | 内容 |
|------|------|
| 文書名 | テスト設計書 |
| プロジェクト名 | Nano Banana Pro Plugin |
| バージョン | 0.1.0 |
| 作成日 | 2025-02-14 |
| 作成者 | kuroneko4423 |

### 改訂履歴

| 版数 | 日付 | 改訂内容 | 担当者 |
|------|------|----------|--------|
| 0.0.1 | 2025-02-14 | 初版作成 | takumi |
| 0.1.0 | 2026-03-02 | model パラメータ関連テストケース追加、auto パラメータテスト追加、Flash 専用パラメータテスト追加、デフォルト値更新 | kuroneko4423 |

---

## 2. テスト方針

### 2.1 テスト対象範囲

| 対象 | ファイル | テスト種別 |
|------|---------|-----------|
| 認証検証機能 | `provider/nanobananapro.py` | 単体テスト |
| 画像生成機能 | `tools/generate_image.py` | 単体テスト |
| 画像編集機能 | `tools/edit_image.py` | 単体テスト |
| 設定ファイル整合性 | `manifest.yaml`, `*.yaml` | 整合性テスト |

### 2.2 テストレベル

| レベル | 対象 | 方法 | 外部依存 |
|-------|------|------|---------|
| 単体テスト | 各クラスのメソッド | pytest + unittest.mock | なし（モック使用） |
| 結合テスト | API 呼び出しフロー全体 | モックサーバー | なし |
| E2E テスト | 実際の Gemini API | 手動実行 | Gemini API キー必要 |

### 2.3 テスト環境

| 項目 | 値 |
|------|-----|
| Python | 3.12 |
| テストフレームワーク | pytest |
| モックライブラリ | `unittest.mock` |
| HTTP モック | `unittest.mock.patch` で `requests.post` / `requests.get` をモック |

### 2.4 推奨テストファイル構成

```
tests/
├── __init__.py
├── test_provider.py          # TC-AUTH: 認証検証テスト
├── test_generate_image.py    # TC-GEN: 画像生成テスト
├── test_edit_image.py        # TC-EDIT: 画像編集テスト
└── test_config.py            # TC-CONF: 設定ファイル整合性テスト
```

---

## 3. テストケース一覧

### 3.1 TC-AUTH: 認証検証テスト

対象: `NanoBananaProProvider._validate_credentials()`

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-AUTH-001 | 正常認証 | モック: GET 200 応答 | `{"gemini_api_key": "valid_key"}` | 例外なし（正常完了） |
| TC-AUTH-002 | API キー空文字 | - | `{"gemini_api_key": ""}` | `ToolProviderCredentialValidationError("Gemini API Key is required.")` |
| TC-AUTH-003 | API キー未設定 | - | `{}` | `ToolProviderCredentialValidationError("Gemini API Key is required.")` |
| TC-AUTH-004 | 無効な API キー（401） | モック: GET 401 応答 | `{"gemini_api_key": "invalid"}` | `ToolProviderCredentialValidationError("Invalid Gemini API Key...")` |
| TC-AUTH-005 | 無効な API キー（403） | モック: GET 403 応答 | `{"gemini_api_key": "forbidden"}` | `ToolProviderCredentialValidationError("Invalid Gemini API Key...")` |
| TC-AUTH-006 | 接続エラー | モック: `requests.ConnectionError` | `{"gemini_api_key": "key"}` | `ToolProviderCredentialValidationError("Failed to connect...")` |
| TC-AUTH-007 | その他例外 | モック: `RuntimeError` 送出 | `{"gemini_api_key": "key"}` | `ToolProviderCredentialValidationError("Credential validation failed: ...")` |

---

### 3.2 TC-GEN: 画像生成テスト

対象: `GenerateImageTool._invoke()`, `GenerateImageTool._extract_error()`

#### 正常系

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-GEN-001 | 正常生成（デフォルト設定） | モック: 200 応答（テキスト + 画像） | `prompt="a cat"` | Blob メッセージ（画像）+ テキストメッセージ。デフォルト: `model="gemini-3-pro-image-preview"`, `aspect_ratio="auto"`, `resolution="auto"` |
| TC-GEN-002 | アスペクト比指定 | モック: 200 応答 | `aspect_ratio="16:9"` | ペイロードの `imageConfig.aspectRatio` が `"16:9"` |
| TC-GEN-003 | 解像度指定 | モック: 200 応答 | `resolution="4K"` | ペイロードの `imageConfig.imageSize` が `"4K"` |
| TC-GEN-004 | temperature 指定 | モック: 200 応答 | `temperature=0.5` | ペイロードの `temperature` が `0.5` |
| TC-GEN-005 | システムプロンプト指定 | モック: 200 応答 | `system_prompt="Be creative"` | ペイロードに `systemInstruction` が含まれる |
| TC-GEN-006 | システムプロンプト未指定 | モック: 200 応答 | `system_prompt=""` | ペイロードに `systemInstruction` が含まれない |

#### エラー系

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-GEN-007 | API キー未設定 | `runtime.credentials` が空 | `prompt="a cat"` | テキスト `"Error: Gemini API Key is not configured."` |
| TC-GEN-008 | API エラー（400） | モック: 400 応答 | `prompt="a cat"` | テキスト `"Gemini API error (400): ..."` |
| TC-GEN-009 | タイムアウト | モック: `requests.Timeout` | `prompt="a cat"` | テキスト `"Error: Request timed out..."` |
| TC-GEN-010 | 接続エラー | モック: `requests.ConnectionError` | `prompt="a cat"` | テキスト `"Error: Failed to connect to the Gemini API."` |
| TC-GEN-011 | 安全性ブロック | モック: `promptFeedback.blockReason="SAFETY"` | `prompt="..."` | テキスト `"Image generation was blocked. Reason: SAFETY..."` |
| TC-GEN-012 | 空 candidates（ブロック理由なし） | モック: `candidates=[]`, `promptFeedback={}` | `prompt="..."` | テキスト `"No image was generated..."` |
| TC-GEN-013 | テキストのみ応答（画像なし） | モック: parts にテキストのみ | `prompt="..."` | テキスト `"The model returned a response but no image was generated..."` |

#### _extract_error テスト

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-GEN-014 | JSON エラーレスポンス | レスポンス: `{"error": {"message": "Bad request"}}` | response オブジェクト | `"Bad request"` |
| TC-GEN-015 | 非 JSON レスポンス | レスポンス: プレーンテキスト | response オブジェクト | テキストの先頭 500 文字 |

#### モデル選択・auto パラメータ・Flash 専用パラメータ

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-GEN-016 | モデル選択（Pro） | モック: 200 応答 | `model="gemini-3-pro-image-preview"` | API URL に `gemini-3-pro-image-preview` が含まれる |
| TC-GEN-017 | モデル選択（Flash） | モック: 200 応答 | `model="gemini-3.1-flash-image-preview"` | API URL に `gemini-3.1-flash-image-preview` が含まれる |
| TC-GEN-018 | auto アスペクト比 | モック: 200 応答 | `aspect_ratio="auto"` | ペイロードの `imageConfig` に `aspectRatio` フィールドが含まれない |
| TC-GEN-019 | auto 解像度 | モック: 200 応答 | `resolution="auto"` | ペイロードの `imageConfig` に `imageSize` フィールドが含まれない |
| TC-GEN-020 | auto 両方（imageConfig 省略） | モック: 200 応答 | `aspect_ratio="auto", resolution="auto"` | ペイロードの `generationConfig` に `imageConfig` 自体が含まれない |
| TC-GEN-021 | Flash 専用アスペクト比 | モック: 200 応答 | `model="gemini-3.1-flash-image-preview", aspect_ratio="21:9"` | ペイロードの `imageConfig.aspectRatio` が `"21:9"` |
| TC-GEN-022 | Flash 専用解像度 | モック: 200 応答 | `model="gemini-3.1-flash-image-preview", resolution="0.5K"` | ペイロードの `imageConfig.imageSize` が `"0.5K"` |

---

### 3.3 TC-EDIT: 画像編集テスト

対象: `EditImageTool._invoke()`, `EditImageTool._read_image()`, `EditImageTool._extract_error()`

#### 正常系

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-EDIT-001 | 正常編集 | モック: 200 応答 | `prompt="edit", image=valid_image` | Blob メッセージ（編集済み画像） |

#### 入力検証

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-EDIT-002 | 画像未指定 | - | `image=None` | テキスト `"Error: An input image is required for editing."` |

#### _read_image テスト - 画像バイト取得

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-EDIT-003 | blob 属性から読み込み | `image_file.blob` が存在 | Dify ファイルオブジェクト | `{"bytes": blob_data, "mime_type": "..."}` |
| TC-EDIT-004 | read() メソッドから読み込み | `image_file.read()` が存在 | ファイルライクオブジェクト | `{"bytes": read_data, "mime_type": "..."}` |
| TC-EDIT-005 | bytes 型から読み込み | `isinstance(image_file, bytes)` | bytes データ | `{"bytes": bytes_data, "mime_type": "image/png"}` |
| TC-EDIT-006 | 未対応型 | いずれの条件も不一致 | int 型 | `None` |

#### _read_image テスト - MIME タイプ判定

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-EDIT-007 | mime_type 属性から判定 | `image_file.mime_type = "image/jpeg"` | Dify ファイルオブジェクト | `mime_type = "image/jpeg"` |
| TC-EDIT-008 | extension: jpg から判定 | `image_file.extension = "jpg"` | Dify ファイルオブジェクト | `mime_type = "image/jpeg"` |
| TC-EDIT-009 | extension: webp から判定 | `image_file.extension = "webp"` | Dify ファイルオブジェクト | `mime_type = "image/webp"` |
| TC-EDIT-010 | デフォルト MIME タイプ | 属性なし | bytes データ | `mime_type = "image/png"` |

#### エラー系

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-EDIT-011 | 画像読み込みエラー（例外） | `_read_image` で例外発生 | 異常な画像オブジェクト | テキスト `"Error reading image: ..."` |
| TC-EDIT-012 | 画像読み込み失敗（None） | `_read_image` が `None` を返却 | 未対応型の画像オブジェクト | テキスト `"Error: Failed to read the input image."` |

#### モデル選択・auto パラメータ・Flash 専用パラメータ

| テスト ID | テスト名 | 前提条件 | 入力 | 期待結果 |
|----------|---------|---------|------|---------|
| TC-EDIT-013 | Flash モデルでの編集 | モック: 200 応答 | `model="gemini-3.1-flash-image-preview", prompt="edit", image=valid_image` | API URL に `gemini-3.1-flash-image-preview` が含まれる |
| TC-EDIT-014 | auto アスペクト比での編集 | モック: 200 応答 | `aspect_ratio="auto", prompt="edit", image=valid_image` | ペイロードの `imageConfig` に `aspectRatio` フィールドが含まれない |
| TC-EDIT-015 | auto 解像度での編集 | モック: 200 応答 | `resolution="auto", prompt="edit", image=valid_image` | ペイロードの `imageConfig` に `imageSize` フィールドが含まれない |
| TC-EDIT-016 | Flash 専用アスペクト比での編集 | モック: 200 応答 | `model="gemini-3.1-flash-image-preview", aspect_ratio="21:9", prompt="edit", image=valid_image` | ペイロードの `imageConfig.aspectRatio` が `"21:9"` |

> **注記**: API エラー、タイムアウト、接続エラー、安全性ブロックのテストは TC-GEN と同一パターンのため省略。実装時は画像生成テストと同様のケースを追加する。

---

### 3.4 TC-CONF: 設定ファイル整合性テスト

対象: `manifest.yaml`, `provider/nanobananapro.yaml`, `tools/*.yaml`

| テスト ID | テスト名 | 確認内容 | 期待結果 |
|----------|---------|---------|---------|
| TC-CONF-001 | manifest.yaml ツール参照 | `plugins.tools` のパスが実在するか | `provider/nanobananapro.yaml` が存在する |
| TC-CONF-002 | プロバイダ YAML ツール参照 | `tools` のパスが実在するか | `tools/generate_image.yaml`, `tools/edit_image.yaml` が存在する |
| TC-CONF-003 | Python ソース参照 | `extra.python.source` のパスが実在するか | 指定された `.py` ファイルが存在する |
| TC-CONF-004 | 多言語キー整合性 | 全 YAML の `label`/`description` に `en_US`, `ja_JP` キーが存在するか | すべてのキーが存在する |

---

## 4. テスト実施方法

### 4.1 単体テスト実行

```bash
# 全テスト実行
pytest tests/ -v

# 特定テストファイルの実行
pytest tests/test_provider.py -v
pytest tests/test_generate_image.py -v
pytest tests/test_edit_image.py -v
pytest tests/test_config.py -v
```

### 4.2 カバレッジ測定

```bash
# カバレッジ付きテスト実行
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# カバレッジ対象ファイル
# - provider/nanobananapro.py
# - tools/generate_image.py
# - tools/edit_image.py
```

### 4.3 モックの基本パターン

#### API レスポンスのモック例

```python
from unittest.mock import patch, MagicMock

@patch("tools.generate_image.requests.post")
def test_generate_image_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [
                    {"text": "A beautiful cat"},
                    {"inlineData": {
                        "mimeType": "image/png",
                        "data": "iVBORw0KGgo="  # Base64 画像データ
                    }}
                ]
            }
        }]
    }
    mock_post.return_value = mock_response
    # ... テスト実行
```

> **注記**: `model` パラメータのテストでは、`mock_post` の呼び出し引数（URL）を検証し、指定したモデル ID（`gemini-3-pro-image-preview` または `gemini-3.1-flash-image-preview`）が URL に含まれていることを確認する。`auto` パラメータのテストでは、`mock_post` に渡された JSON ペイロードを検証し、`imageConfig` の有無やフィールドの省略を確認する。

#### Dify ファイルオブジェクトのモック例

```python
from unittest.mock import MagicMock

# blob 属性を持つファイルオブジェクト
mock_file = MagicMock()
mock_file.blob = b"\x89PNG\r\n..."
mock_file.mime_type = "image/png"

# extension 属性を持つファイルオブジェクト
mock_file = MagicMock(spec=["blob", "extension"])
mock_file.blob = b"\xff\xd8\xff\xe0..."
mock_file.extension = "jpg"
```

### 4.4 E2E テスト（手動）

E2E テストは実際の Gemini API キーを使用して手動で実施する。

| テスト項目 | 手順 | 確認事項 |
|-----------|------|---------|
| 認証検証 | Dify プラグイン設定画面で API キーを入力 | 正常に認証が通ること |
| 画像生成 | ワークフローで画像生成ツールを実行 | 画像が生成されること |
| 画像編集 | ワークフローで画像編集ツールに画像と指示を入力 | 編集済み画像が返却されること |
| エラー表示 | 無効な API キーでツールを実行 | 適切なエラーメッセージが表示されること |
