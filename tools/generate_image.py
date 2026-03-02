import base64
import json
from collections.abc import Generator
from typing import Any

import requests

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GenerateImageTool(Tool):
    """
    Generate images from text prompts using Nano Banana Pro
    (Gemini 3 Pro Image) or Nano Banana 2
    (Gemini 3.1 Flash Image).

    Uses the Gemini API generateContent endpoint with
    responseModalities set to include IMAGE for native
    image generation.
    """

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage]:
        # --- Extract parameters ---
        prompt = tool_parameters["prompt"]
        model_id = tool_parameters.get(
            "model", "gemini-3-pro-image-preview"
        )
        aspect_ratio = tool_parameters.get("aspect_ratio", "auto")
        resolution = tool_parameters.get("resolution", "auto")
        temperature = tool_parameters.get("temperature", 1.0)
        system_prompt = tool_parameters.get("system_prompt", "")

        # --- Get API key from provider credentials ---
        api_key = self.runtime.credentials.get("gemini_api_key", "")
        if not api_key:
            yield self.create_text_message(
                "Error: Gemini API Key is not configured."
            )
            return

        # --- Build request payload ---
        generation_config: dict = {
            "responseModalities": ["TEXT", "IMAGE"],
            "temperature": temperature,
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
                    "parts": [{"text": prompt}]
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
            url = (
                f"{GEMINI_API_BASE}/models/"
                f"{model_id}:generateContent"
            )
            response = requests.post(
                url,
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=120,  # Image generation can take longer
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
                "Error: Request timed out. Image generation may take up to 2 minutes. "
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
            # Check for prompt feedback (safety block)
            prompt_feedback = result.get("promptFeedback", {})
            block_reason = prompt_feedback.get("blockReason", "")
            if block_reason:
                yield self.create_text_message(
                    f"Image generation was blocked. Reason: {block_reason}. "
                    "Please modify your prompt and try again."
                )
            else:
                yield self.create_text_message(
                    "No image was generated. Please try a different prompt."
                )
            return

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        image_found = False
        for part in parts:
            # Handle text parts (model may return descriptive text)
            if "text" in part:
                yield self.create_text_message(part["text"])

            # Handle image parts
            if "inlineData" in part:
                inline_data = part["inlineData"]
                mime_type = inline_data.get("mimeType", "image/png")
                image_b64 = inline_data.get("data", "")

                if image_b64:
                    image_bytes = base64.b64decode(image_b64)
                    yield self.create_blob_message(
                        blob=image_bytes,
                        meta={
                            "mime_type": mime_type,
                        },
                    )
                    image_found = True

        if not image_found:
            yield self.create_text_message(
                "The model returned a response but no image was generated. "
                "Try rephrasing your prompt to focus on visual content."
            )

    def _extract_error(self, response: requests.Response) -> str:
        """Extract a readable error message from the API response."""
        try:
            error_data = response.json()
            error = error_data.get("error", {})
            return error.get("message", response.text[:500])
        except (json.JSONDecodeError, ValueError):
            return response.text[:500]
