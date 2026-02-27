from collections.abc import Generator
from typing import Any

import base64

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class DoubaoSeedream50LiteTool(Tool):
    DEFAULT_MODEL = "doubao-seedream-5-0-lite-260128"
    DEFAULT_SIZE = "2K"
    DEFAULT_OUTPUT_FORMAT = "jpeg"
    DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    CUSTOM_SIZE_MIN_PIXELS = 3686400
    CUSTOM_SIZE_MAX_PIXELS = 10404496

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str:
        base_url = (base_url or "").strip()
        if not base_url:
            return DoubaoSeedream50LiteTool.DEFAULT_ARK_BASE_URL
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

    @staticmethod
    def _fetch_file_as_data_url(file_obj: Any) -> str:
        url = getattr(file_obj, "url", None)
        mime_type = getattr(file_obj, "mime_type", None)
        if not url or not mime_type:
            raise ValueError("Invalid image file: missing url or mime_type")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        base64_data = base64.b64encode(response.content).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"

    def _build_images_payload(self, files: Any) -> list[str]:
        if not files or files == [None]:
            return []

        if not isinstance(files, list):
            raise ValueError("Invalid parameter: image must be a list of files")

        if len(files) > 14:
            raise ValueError("参考图最多支持 14 张")

        return [self._fetch_file_as_data_url(file_obj) for file_obj in files]

    def _normalize_size(self, tool_parameters: dict[str, Any]) -> str:
        size = (tool_parameters.get("size") or self.DEFAULT_SIZE) if tool_parameters is not None else self.DEFAULT_SIZE
        if size != "customize":
            return str(size)

        width = tool_parameters.get("width")
        height = tool_parameters.get("height")
        if width is None or height is None:
            raise ValueError("请填写图片宽度和高度")

        try:
            width_i = int(width)
            height_i = int(height)
        except Exception as e:
            raise ValueError("图片宽度和高度必须为整数") from e

        if width_i <= 14 or height_i <= 14:
            raise ValueError("图片宽度和高度必须大于 14px")

        total_pixels = width_i * height_i
        if total_pixels < self.CUSTOM_SIZE_MIN_PIXELS or total_pixels > self.CUSTOM_SIZE_MAX_PIXELS:
            raise ValueError(
                f"总像素值(宽*高)必须在[{self.CUSTOM_SIZE_MIN_PIXELS}, {self.CUSTOM_SIZE_MAX_PIXELS}]之间"
            )

        ratio = width_i / height_i
        if ratio < 1 / 16 or ratio > 16:
            raise ValueError("图片宽高比必须在[1/16, 16]之间")

        return f"{width_i}x{height_i}"

    @staticmethod
    def _normalize_output_format(output_format: Any) -> str:
        value = (output_format or DoubaoSeedream50LiteTool.DEFAULT_OUTPUT_FORMAT)
        if not isinstance(value, str):
            raise ValueError("output_format must be a string")
        normalized = value.strip().lower()
        if normalized not in {"jpeg", "png"}:
            raise ValueError("output_format must be one of: jpeg, png")
        return normalized

    @staticmethod
    def _parse_images_response_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
        if not isinstance(payload, dict):
            raise RuntimeError("Ark response is not a JSON object")

        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message") or "Ark API error"
            raise RuntimeError(str(message))

        data = payload.get("data")
        if not data:
            raise RuntimeError("生成图片失败")

        result: list[dict[str, str]] = []
        first_error_message: str | None = None

        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                if "url" in item and item.get("url"):
                    result.append({"url": str(item["url"]), "size": str(item.get("size") or "")})
                    continue
                item_error = item.get("error")
                if first_error_message is None and isinstance(item_error, dict):
                    first_error_message = str(item_error.get("message") or "生成图片失败")

        if not result:
            raise RuntimeError(first_error_message or "生成图片失败")

        return result

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        credentials = self._get_credentials()
        api_key = (credentials.get("ARK_API_KEY") or credentials.get("ark_api_key") or "").strip()
        if not api_key:
            raise ValueError("Missing provider credential: ARK_API_KEY")

        prompt = tool_parameters.get("prompt")
        if not prompt:
            raise ValueError("请填写提示语")

        generation = self._coerce_bool(tool_parameters.get("sequential_image_generation"), default=False)
        watermark = self._coerce_bool(tool_parameters.get("watermark"), default=False)
        web_search = self._coerce_bool(tool_parameters.get("web_search"), default=False)

        output_format = self._normalize_output_format(tool_parameters.get("output_format"))
        sequential_image_generation = "auto" if generation else "disabled"

        files = tool_parameters.get("image")
        image = self._build_images_payload(files)

        size = self._normalize_size(tool_parameters)
        base_url = self._normalize_base_url(credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url"))

        try:
            from volcenginesdkarkruntime import Ark
            from volcenginesdkarkruntime.types.images import ContentGenerationTool
        except ImportError as e:
            raise RuntimeError(
                "Missing dependency `volcengine-python-sdk[ark]`. "
                "Please ensure it is installed from requirements.txt."
            ) from e

        tools: list | None = [ContentGenerationTool(type="web_search")] if web_search else None

        client = Ark(api_key=api_key, base_url=base_url)

        try:
            response = client.images.generate(
                model=self.DEFAULT_MODEL,
                prompt=prompt,
                image=image,
                size=size,
                sequential_image_generation=sequential_image_generation,
                response_format="url",
                watermark=watermark,
                output_format=output_format,
                tools=tools,
            )

            data = getattr(response, "data", None)
            if not data:
                raise RuntimeError("生成图片失败")

            result: list[dict[str, str]] = []
            if isinstance(data, list):
                for img in data:
                    url = getattr(img, "url", None)
                    if url:
                        result.append({"url": str(url), "size": str(getattr(img, "size", "") or "")})

            if not result:
                raise RuntimeError("生成图片失败")
        except TypeError:
            url = f"{base_url}/images/generations"
            payload: dict[str, Any] = {
                "model": self.DEFAULT_MODEL,
                "prompt": prompt,
                "size": size,
                "sequential_image_generation": sequential_image_generation,
                "response_format": "url",
                "watermark": watermark,
                "output_format": output_format,
            }
            if image:
                payload["image"] = image
            if tools:
                payload["tools"] = [t.model_dump(mode="json") for t in tools]

            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            result = self._parse_images_response_payload(resp.json())

        markdown_images = "".join([f"![]({img['url']})" for img in result])
        yield self.create_text_message(markdown_images)
        yield self.create_variable_message("images", result)
