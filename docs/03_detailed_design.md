# 詳細設計書 - Nano Banana Pro Plugin

## 1. 文書情報

| 項目 | 内容 |
|------|------|
| 文書名 | 詳細設計書 |
| プロジェクト名 | Nano Banana Pro Plugin |
| バージョン | 0.0.1 |
| 作成日 | 2025-02-14 |
| 作成者 | takumi |

### 改訂履歴

| 版数 | 日付 | 改訂内容 | 担当者 |
|------|------|----------|--------|
| 0.0.1 | 2025-02-14 | 初版作成 | takumi |

---

## 2. クラス構成

### 2.1 クラス継承関係図

```
dify_plugin.ToolProvider
    └── NanoBananaProProvider          (provider/nanobananapro.py)

dify_plugin.Tool
    ├── GenerateImageTool              (tools/generate_image.py)
    └── EditImageTool                  (tools/edit_image.py)
```

### 2.2 クラス一覧

| クラス名 | 基底クラス | ファイルパス | 行数 | 責務 |
|---------|-----------|-------------|------|------|
| `NanoBananaProProvider` | `ToolProvider` | `provider/nanobananapro.py` | 49 行 | Gemini API キーの検証 |
| `GenerateImageTool` | `Tool` | `tools/generate_image.py` | 155 行 | テキストからの画像生成 |
| `EditImageTool` | `Tool` | `tools/edit_image.py` | 221 行 | 既存画像の自然言語編集 |

---

## 3. NanoBananaProProvider クラス

### 3.1 クラス定義

- **ファイル**: `provider/nanobananapro.py`
- **基底クラス**: `dify_plugin.ToolProvider`
- **インポート**: `typing.Any`, `dify_plugin.ToolProvider`, `dify_plugin.errors.tool.ToolProviderCredentialValidationError`, `requests`

### 3.2 定数

| 定数名 | 値 | スコープ |
|--------|-----|---------|
| `GEMINI_API_BASE` | `"https://generativelanguage.googleapis.com/v1beta"` | モジュールレベル |

### 3.3 メソッド詳細

#### `_validate_credentials(self, credentials: dict[str, Any]) -> None`

認証情報の有効性を検証するオーバーライドメソッド。

| 項目 | 内容 |
|------|------|
| 引数 | `credentials: dict[str, Any]` - `gemini_api_key` キーを含む辞書 |
| 戻り値 | `None`（失敗時は例外を送出） |
| 例外 | `ToolProviderCredentialValidationError` |

**処理ロジック**:

```python
1. api_key = credentials.get("gemini_api_key", "")
2. if not api_key:
     raise ToolProviderCredentialValidationError("Gemini API Key is required.")
3. try:
     response = requests.get(
         f"{GEMINI_API_BASE}/models",
         params={"key": api_key},
         timeout=10
     )
     if response.status_code == 401 or response.status_code == 403:
         raise ToolProviderCredentialValidationError("Invalid Gemini API Key...")
     response.raise_for_status()
   except ToolProviderCredentialValidationError:
     raise  # 再送出
   except requests.ConnectionError:
     raise ToolProviderCredentialValidationError("Failed to connect...")
   except Exception as e:
     raise ToolProviderCredentialValidationError(f"Credential validation failed: {str(e)}")
```

**例外処理の順序**: `ToolProviderCredentialValidationError` を最初にキャッチして再送出することで、内部で送出した認証エラーが汎用 `Exception` ハンドラに捕捉されることを防いでいる。

---

## 4. GenerateImageTool クラス

### 4.1 クラス定義

- **ファイル**: `tools/generate_image.py`
- **基底クラス**: `dify_plugin.Tool`
- **インポート**: `base64`, `json`, `collections.abc.Generator`, `typing.Any`, `requests`, `dify_plugin.Tool`, `dify_plugin.entities.tool.ToolInvokeMessage`

### 4.2 定数

| 定数名 | 値 | スコープ |
|--------|-----|---------|
| `GEMINI_API_BASE` | `"https://generativelanguage.googleapis.com/v1beta"` | モジュールレベル |
| `MODEL_ID` | `"gemini-3-pro-image-preview"` | モジュールレベル |

### 4.3 メソッド詳細

#### `_invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]`

画像生成の主処理を実行するオーバーライドメソッド。ジェネレータパターンにより、`yield` で結果を逐次返却する。

| 項目 | 内容 |
|------|------|
| 引数 | `tool_parameters: dict[str, Any]` - ツールパラメータ辞書 |
| 戻り値 | `Generator[ToolInvokeMessage]` - メッセージのジェネレータ |

**パラメータ抽出ロジック**:

```python
prompt = tool_parameters["prompt"]                          # 必須（KeyError の場合は未処理）
aspect_ratio = tool_parameters.get("aspect_ratio", "1:1")   # デフォルト: "1:1"
resolution = tool_parameters.get("resolution", "1K")         # デフォルト: "1K"
temperature = tool_parameters.get("temperature", 1.0)        # デフォルト: 1.0
system_prompt = tool_parameters.get("system_prompt", "")     # デフォルト: ""
```

**API ペイロード構造**:

```json
{
  "contents": [
    {
      "parts": [{"text": "<prompt>"}]
    }
  ],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"],
    "temperature": 1.0,
    "imageConfig": {
      "aspectRatio": "1:1",
      "imageSize": "1K"
    }
  }
}
```

`system_prompt` が空でない場合、以下が追加される：

```json
{
  "systemInstruction": {
    "parts": [{"text": "<system_prompt>"}]
  }
}
```

**レスポンスパース処理**:

```python
for part in candidates[0]["content"]["parts"]:
    if "text" in part:
        yield self.create_text_message(part["text"])
    if "inlineData" in part:
        image_bytes = base64.b64decode(part["inlineData"]["data"])
        yield self.create_blob_message(
            blob=image_bytes,
            meta={"mime_type": part["inlineData"]["mimeType"]}
        )
```

> **注記**: `if "text"` と `if "inlineData"` は排他的な `elif` ではなく、両方の `if` で判定している。理論上、1 つの part に text と inlineData の両方が含まれる可能性に対応する設計。

#### `_extract_error(self, response: requests.Response) -> str`

API レスポンスからエラーメッセージを抽出するヘルパーメソッド。

| 項目 | 内容 |
|------|------|
| 引数 | `response: requests.Response` |
| 戻り値 | `str` - エラーメッセージ文字列 |

**処理ロジック**:

```python
try:
    error_data = response.json()                    # JSON パースを試行
    error = error_data.get("error", {})
    return error.get("message", response.text[:500]) # message がなければ生テキスト
except (json.JSONDecodeError, ValueError):
    return response.text[:500]                       # JSON パース失敗時は生テキスト
```

---

## 5. EditImageTool クラス

### 5.1 クラス定義

- **ファイル**: `tools/edit_image.py`
- **基底クラス**: `dify_plugin.Tool`
- **インポート**: GenerateImageTool と同一

### 5.2 定数

GenerateImageTool と同一（`GEMINI_API_BASE`, `MODEL_ID`）。

### 5.3 メソッド詳細

#### `_invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]`

画像編集の主処理。GenerateImageTool の `_invoke` との差分は以下の通り：

| 差分項目 | GenerateImageTool | EditImageTool |
|---------|-------------------|---------------|
| `temperature` パラメータ | あり | なし |
| `image` パラメータ | なし | あり（必須） |
| 画像入力の検証 | なし | `image_file` の空チェック |
| 画像読み込み処理 | なし | `_read_image()` + Base64 エンコード |
| ペイロードの parts | `[{text}]` | `[{text}, {inlineData}]` |
| generationConfig | `temperature` を含む | `temperature` を含まない |

**画像編集時のペイロード構造**:

```json
{
  "contents": [
    {
      "parts": [
        {"text": "<edit_instructions>"},
        {
          "inlineData": {
            "mimeType": "image/png",
            "data": "<base64_encoded_image>"
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

#### `_read_image(self, image_file: Any) -> dict | None`

Dify ファイルオブジェクトから画像データを読み込むヘルパーメソッド。

| 項目 | 内容 |
|------|------|
| 引数 | `image_file: Any` - Dify のファイルオブジェクト |
| 戻り値 | `dict` (`{"bytes": bytes, "mime_type": str}`) または `None` |

**画像バイト取得の 3 パターン分岐**:

```
image_file の型判定
  │
  ├── hasattr(image_file, "blob") = True
  │   → image_bytes = image_file.blob
  │
  ├── hasattr(image_file, "read") = True
  │   → image_bytes = image_file.read()
  │
  ├── isinstance(image_file, bytes) = True
  │   → image_bytes = image_file
  │
  └── いずれにも該当しない
      → return None
```

**MIME タイプ判定の優先順位**:

```
1. image_file.mime_type 属性が存在し、値が truthy
   → mime_type = image_file.mime_type

2. image_file.extension 属性が存在
   → ext = image_file.extension.lower().lstrip(".")
   → mime_map から変換（見つからなければ "image/png"）

3. いずれの属性もない
   → mime_type = "image/png"（デフォルト）
```

**MIME タイプ変換マップ**:

| 拡張子 | MIME タイプ |
|--------|-----------|
| `jpg` | `image/jpeg` |
| `jpeg` | `image/jpeg` |
| `png` | `image/png` |
| `webp` | `image/webp` |
| `heic` | `image/heic` |
| `heif` | `image/heif` |

> **注記**: `_read_image` メソッド内部の `try-except` は `Exception` をキャッチして `None` を返す。呼び出し元の `_invoke` メソッドでも別途 `try-except` で囲んでおり、二重のエラーハンドリング構造となっている。

#### `_extract_error(self, response: requests.Response) -> str`

GenerateImageTool の `_extract_error` と同一の実装。

---

## 6. エントリーポイント

### 6.1 main.py

```python
import sys
from dify_plugin import DifyPluginEnv, Plugin

plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=120))

if __name__ == "__main__":
    plugin.run()
```

**起動シーケンス**:

1. `DifyPluginEnv` インスタンスを生成（`MAX_REQUEST_TIMEOUT=120` 秒）
2. `Plugin` インスタンスを生成
3. `__main__` 実行時に `plugin.run()` でプラグインデーモンを起動
4. Dify Plugin Runtime がプロバイダとツールの YAML 定義を読み込み、クラスを自動登録

---

## 7. 設定ファイル詳細

### 7.1 manifest.yaml

プラグインのメタデータと実行環境を定義する。

| フィールド | 値 | 説明 |
|-----------|-----|------|
| `version` | `0.0.1` | プラグインバージョン |
| `type` | `plugin` | パッケージタイプ |
| `author` | `"takumi"` | 作成者 |
| `name` | `"nanobananapro"` | プラグイン内部名 |
| `description` | 多言語 (en_US, ja_JP, zh_Hans) | プラグイン説明 |
| `icon` | `"icon.svg"` | `_assets/` 配下のアイコン |
| `label` | 多言語 | 表示名 |
| `created_at` | `"2025-02-14T00:00:00.000Z"` | 作成日時 |
| `resource.memory` | `268435456` (256 MB) | メモリ上限 |
| `resource.permission.tool.enabled` | `true` | ツール提供の許可 |
| `resource.permission.storage.enabled` | `true` | ストレージアクセスの許可 |
| `resource.permission.storage.size` | `1048576` (1 MB) | ストレージ上限 |
| `plugins.tools` | `["provider/nanobananapro.yaml"]` | ツールプロバイダ定義への参照 |
| `meta.arch` | `["amd64", "arm64"]` | 対応アーキテクチャ |
| `meta.runner.language` | `"python"` | 実行言語 |
| `meta.runner.version` | `"3.12"` | Python バージョン |
| `meta.runner.entrypoint` | `"main"` | エントリーポイント（main.py） |

### 7.2 provider/nanobananapro.yaml

プロバイダの定義ファイル。認証情報スキーマとツール参照を含む。

| フィールド | 説明 |
|-----------|------|
| `identity` | プロバイダの名前、ラベル、説明、アイコン、タグ |
| `credentials_for_provider.gemini_api_key` | API キーのスキーマ（type: secret-input, required: true） |
| `tools` | ツール定義への参照パス（`tools/generate_image.yaml`, `tools/edit_image.yaml`） |
| `extra.python.source` | Python ソースファイルへの参照（`provider/nanobananapro.py`） |

### 7.3 tools/generate_image.yaml

画像生成ツールの定義ファイル。

| フィールド | 説明 |
|-----------|------|
| `identity` | ツールの名前（`generate_image`）、ラベル |
| `description.human` | ユーザー向け説明（多言語） |
| `description.llm` | LLM 向け説明（英語のみ、ツール選択の判断材料） |
| `parameters` | 5 パラメータの定義（prompt, system_prompt, aspect_ratio, resolution, temperature） |
| `extra.python.source` | Python ソースファイルへの参照 |

**`form` フィールドの区分**:

| 値 | 説明 |
|----|------|
| `llm` | Dify の LLM エージェントがワークフロー実行中に値を決定する |
| `form` | ユーザーがプラグイン設定の UI フォームで事前に入力する |

### 7.4 tools/edit_image.yaml

画像編集ツールの定義ファイル。generate_image.yaml との差分：

| 差分 | 内容 |
|------|------|
| `parameters.image` | `type: file` の入力パラメータ（画像生成にはない） |
| `parameters.temperature` | 画像編集には存在しない |
| `description.llm` | 編集操作に特化した LLM 向け説明 |

---

## 8. 共通パターン・設計判断

### 8.1 エラーハンドリング戦略

両ツールクラスは以下の階層的な例外キャッチパターンを採用している：

```python
try:
    response = requests.post(url, ...)
    if response.status_code != 200:
        # HTTP エラーを先に処理
        yield self.create_text_message(f"Gemini API error ...")
        return
    result = response.json()
except requests.Timeout:          # 1. タイムアウト（最も具体的）
    yield ...
    return
except requests.ConnectionError:  # 2. 接続エラー
    yield ...
    return
except Exception as e:            # 3. その他すべて（最も一般的）
    yield ...
    return
```

エラーメッセージは `yield self.create_text_message()` で返却し、その後 `return` でジェネレータを終了する。例外を送出するのではなく、ユーザー向けのテキストメッセージとしてエラー情報を返す設計としている。

### 8.2 定数の重複

`GEMINI_API_BASE` は以下の 3 ファイルで個別に定義されている：

- `provider/nanobananapro.py`（9 行目）
- `tools/generate_image.py`（12 行目）
- `tools/edit_image.py`（12 行目）

`MODEL_ID` は以下の 2 ファイルで定義されている：

- `tools/generate_image.py`（13 行目）
- `tools/edit_image.py`（13 行目）

各モジュールが独立して動作できるよう、意図的に重複定義としている。

### 8.3 ジェネレータパターンの採用

`_invoke` メソッドは `Generator[ToolInvokeMessage]` を返す。`yield` によりメッセージを逐次返却することで、以下の利点がある：

- 1 回の呼び出しで複数のメッセージ（テキスト + 画像）を返却可能
- エラー発生時に `return` で即座にジェネレータを終了可能
- Dify Plugin Runtime のストリーミング対応と整合

### 8.4 セキュリティ考慮事項

| 項目 | 対策 |
|------|------|
| API キーの保管 | Dify の `secret-input` 型（暗号化保管） |
| API キーの送信 | HTTPS + URL クエリパラメータ（Gemini API の仕様に準拠） |
| API キーの露出防止 | エラーメッセージに API キーを含めない |
| コンテンツ安全性 | Gemini API の安全性フィルタ + `blockReason` の検出と通知 |
| 生成画像の識別 | SynthID ウォーターマーク（Gemini API 側で自動付与） |
