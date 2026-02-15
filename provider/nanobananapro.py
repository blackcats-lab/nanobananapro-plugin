from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

import requests


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class NanoBananaProProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate Gemini API credentials by making a lightweight request
        to list available models.
        """
        api_key = credentials.get("gemini_api_key", "")
        if not api_key:
            raise ToolProviderCredentialValidationError(
                "Gemini API Key is required."
            )

        try:
            # Use the models.list endpoint for lightweight validation
            response = requests.get(
                f"{GEMINI_API_BASE}/models",
                params={"key": api_key},
                timeout=10,
            )

            if response.status_code == 401 or response.status_code == 403:
                raise ToolProviderCredentialValidationError(
                    "Invalid Gemini API Key. Please check your credentials."
                )

            response.raise_for_status()

        except ToolProviderCredentialValidationError:
            raise
        except requests.ConnectionError:
            raise ToolProviderCredentialValidationError(
                "Failed to connect to the Gemini API. Please check your network."
            )
        except Exception as e:
            raise ToolProviderCredentialValidationError(
                f"Credential validation failed: {str(e)}"
            )
