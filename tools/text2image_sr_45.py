from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class DoubaoSeedreamTool(Tool):
    DEFAULT_MODEL = "doubao-seedream-4-5-251128"
    DEFAULT_SIZE = "2K"
    DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str:
        base_url = (base_url or "").strip()
        if not base_url:
            return DoubaoSeedreamTool.DEFAULT_ARK_BASE_URL
        return base_url.rstrip("/")

    @staticmethod
    def _coerce_bool(value: Any, *, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y", "on"}:
                return True
            if normalized in {"false", "0", "no", "n", "off"}:
                return False
        return default

    def _get_credentials(self) -> dict[str, Any]:
        runtime = getattr(self, "runtime", None)
        if runtime is None:
            return {}

        credentials = getattr(runtime, "credentials", None)
        if isinstance(credentials, dict):
            return credentials

        if callable(credentials):
            try:
                maybe_credentials = credentials()
                if isinstance(maybe_credentials, dict):
                    return maybe_credentials
            except Exception:
                pass

        get_credentials = getattr(runtime, "get_credentials", None)
        if callable(get_credentials):
            try:
                maybe_credentials = get_credentials()
                if isinstance(maybe_credentials, dict):
                    return maybe_credentials
            except Exception:
                pass

        return {}

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        credentials = self._get_credentials()
        api_key = (credentials.get("ARK_API_KEY") or credentials.get("ark_api_key") or "").strip()
        if not api_key:
            raise ValueError("Missing provider credential: ARK_API_KEY")

        base_url = self._normalize_base_url(credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url"))

        prompt = (tool_parameters.get("prompt") or tool_parameters.get("query") or "").strip()
        if not prompt:
            raise ValueError("Parameter `prompt` is required")

        model = (tool_parameters.get("model") or self.DEFAULT_MODEL).strip() or self.DEFAULT_MODEL
        size_value = tool_parameters.get("size")
        if isinstance(size_value, str):
            size = size_value.strip() or self.DEFAULT_SIZE
        elif size_value is None:
            size = self.DEFAULT_SIZE
        else:
            size = str(size_value)
        watermark = self._coerce_bool(tool_parameters.get("watermark"), default=False)

        try:
            from volcenginesdkarkruntime import Ark
        except ImportError as e:
            raise RuntimeError(
                "Missing dependency `volcengine-python-sdk[ark]`. "
                "Please ensure it is installed from requirements.txt."
            ) from e

        client = Ark(api_key=api_key, base_url=base_url)
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            response_format="url",
            watermark=watermark,
        )

        url: str | None = None
        data = getattr(response, "data", None)
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                url = first.get("url")
            else:
                url = getattr(first, "url", None)

        if not url and isinstance(response, dict):
            try:
                url = response["data"][0]["url"]
            except Exception:
                url = None

        if not url:
            raise RuntimeError("Ark images.generate did not return an image URL")

        yield self.create_image_message(url)
        yield self.create_json_message(
            {
                "model": model,
                "size": size,
                "watermark": watermark,
                "url_expires_in": "24h",
                "note": "Ark image URL is typically valid for 24 hours.",
            }
        )
