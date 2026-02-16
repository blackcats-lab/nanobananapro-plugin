import base64
import json
from collections.abc import Generator
from typing import Any

import requests

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
MODEL_ID = "gemini-3-pro-image-preview"


class EditImageTool(Tool):
    """
    Edit an existing image using natural language instructions
    with Nano Banana Pro (Gemini 3 Pro Image).

    Sends the input image along with text instructions to the Gemini API
    generateContent endpoint with responseModalities set to include IMAGE.
    """

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage]:
        # --- Extract parameters ---
        prompt = tool_parameters["prompt"]
        image_file = tool_parameters.get("image")
        aspect_ratio = tool_parameters.get("aspect_ratio", "auto")
        resolution = tool_parameters.get("resolution", "auto")
        system_prompt = tool_parameters.get("system_prompt", "")

        # --- Validate image input ---
        if not image_file:
            yield self.create_text_message(
                "Error: An input image is required for editing."
            )
            return

        # --- Get API key from provider credentials ---
        api_key = self.runtime.credentials.get("gemini_api_key", "")
        if not api_key:
            yield self.create_text_message(
                "Error: Gemini API Key is not configured."
            )
            return

        # --- Read and encode the input image ---
        try:
            image_data = self._read_image(image_file)
            if not image_data:
                yield self.create_text_message(
                    "Error: Failed to read the input image."
                )
                return

            image_b64 = base64.b64encode(image_data["bytes"]).decode("utf-8")
            mime_type = image_data["mime_type"]
        except Exception as e:
            yield self.create_text_message(
                f"Error reading image: {str(e)}"
            )
            return

        # --- Build request payload ---
        generation_config: dict = {
            "responseModalities": ["TEXT", "IMAGE"],
        }

        image_config: dict = {}
        if aspect_ratio != "auto":
            image_config["aspectRatio"] = aspect_ratio
        if resolution != "auto":
            image_config["imageSize"] = resolution
        if image_config:
            generation_config["imageConfig"] = image_config

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_b64,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": generation_config,
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        # --- Call Gemini API ---
        try:
            url = f"{GEMINI_API_BASE}/models/{MODEL_ID}:generateContent"
            response = requests.post(
                url,
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )

            if response.status_code != 200:
                error_detail = self._extract_error(response)
                yield self.create_text_message(
                    f"Gemini API error ({response.status_code}): {error_detail}"
                )
                return

            result = response.json()

        except requests.Timeout:
            yield self.create_text_message(
                "Error: Request timed out. Image editing may take up to 2 minutes. "
                "Please try again or use a lower resolution."
            )
            return
        except requests.ConnectionError:
            yield self.create_text_message(
                "Error: Failed to connect to the Gemini API."
            )
            return
        except Exception as e:
            yield self.create_text_message(f"Error: {str(e)}")
            return

        # --- Parse response ---
        candidates = result.get("candidates", [])
        if not candidates:
            prompt_feedback = result.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason", "")
            if block_reason:
                yield self.create_text_message(
                    f"Image editing was blocked. Reason: {block_reason}. "
                    "Please modify your instructions and try again."
                )
            else:
                yield self.create_text_message(
                    "No edited image was generated. Please try different instructions."
                )
            return

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        image_found = False
        for part in parts:
            if "text" in part:
                yield self.create_text_message(part["text"])

            if "inlineData" in part:
                inline_data = part["inlineData"]
                out_mime_type = inline_data.get("mimeType", "image/png")
                out_image_b64 = inline_data.get("data", "")

                if out_image_b64:
                    image_bytes = base64.b64decode(out_image_b64)
                    yield self.create_blob_message(
                        blob=image_bytes,
                        meta={
                            "mime_type": out_mime_type,
                        },
                    )
                    image_found = True

        if not image_found:
            yield self.create_text_message(
                "The model returned a response but no edited image was generated. "
                "Try rephrasing your edit instructions."
            )

    def _read_image(self, image_file: Any) -> dict | None:
        """
        Read image file content from the Dify file object.
        Returns dict with 'bytes' and 'mime_type', or None on failure.
        """
        try:
            # Handle Dify file object
            if hasattr(image_file, "blob"):
                image_bytes = image_file.blob
            elif hasattr(image_file, "read"):
                image_bytes = image_file.read()
            elif isinstance(image_file, bytes):
                image_bytes = image_file
            else:
                return None

            # Determine MIME type
            mime_type = "image/png"
            if hasattr(image_file, "mime_type") and image_file.mime_type:
                mime_type = image_file.mime_type
            elif hasattr(image_file, "extension"):
                ext = image_file.extension.lower().lstrip(".")
                mime_map = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                    "heic": "image/heic",
                    "heif": "image/heif",
                }
                mime_type = mime_map.get(ext, "image/png")

            return {"bytes": image_bytes, "mime_type": mime_type}

        except Exception:
            return None

    def _extract_error(self, response: requests.Response) -> str:
        """Extract a readable error message from the API response."""
        try:
            error_data = response.json()
            error = error_data.get("error", {})
            return error.get("message", response.text[:500])
        except (json.JSONDecodeError, ValueError):
            return response.text[:500]
