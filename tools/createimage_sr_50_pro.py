from collections.abc import Generator
from typing import Any

import base64

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class DoubaoSeedream50ProTool(Tool):
    DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"
    DEFAULT_SIZE = "2K"
    DEFAULT_OUTPUT_FORMAT = "jpeg"
    DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    MAX_REFERENCE_IMAGES = 10
    CUSTOM_SIZE_MIN_PIXELS = 921600
    CUSTOM_SIZE_MAX_PIXELS = 4624220
    SUPPORTED_SIZES = {
        "1K",
        "2K",
        "1024x1024",
        "1152x864",
        "864x1152",
        "1424x800",
        "800x1424",
        "1248x832",
        "832x1248",
        "1568x672",
        "2048x2048",
        "2368x1776",
        "1776x2368",
        "2816x1584",
        "1584x2816",
        "2496x1664",
        "1664x2496",
        "3136x1344",
    }

    @staticmethod
    def _normalize_base_url(base_url: str | None) -> str:
        base_url = (base_url or "").strip()
        if not base_url:
            return DoubaoSeedream50ProTool.DEFAULT_ARK_BASE_URL
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

    def _build_images_payload(self, files: Any, image_urls: Any) -> list[str]:
        file_objects: list[Any] = []
        if files and files != [None]:
            if not isinstance(files, list):
                raise ValueError("Invalid parameter: image must be a list of files")
            file_objects = files

        url_list: list[str] = []
        if image_urls:
            if not isinstance(image_urls, str):
                raise ValueError("Invalid parameter: image_urls must be a string")
            url_list = [
                url.strip()
                for url in image_urls.replace("，", ",").split(",")
                if url.strip()
            ]

        if len(file_objects) + len(url_list) > self.MAX_REFERENCE_IMAGES:
            raise ValueError(f"参考图最多支持 {self.MAX_REFERENCE_IMAGES} 张")

        return [self._fetch_file_as_data_url(file_obj) for file_obj in file_objects] + url_list

    def _normalize_size(self, tool_parameters: dict[str, Any]) -> str:
        size = str(tool_parameters.get("size") or self.DEFAULT_SIZE)
        if size != "customize":
            if size not in self.SUPPORTED_SIZES:
                raise ValueError("图片尺寸必须为 1K、2K、官方预设尺寸或自定义尺寸")
            return size

        width = tool_parameters.get("width")
        height = tool_parameters.get("height")
        if width is None or height is None:
            raise ValueError("请填写图片宽度和高度")

        try:
            width_i = int(width)
            height_i = int(height)
        except (TypeError, ValueError) as e:
            raise ValueError("图片宽度和高度必须为整数") from e

        if width_i <= 14 or height_i <= 14:
            raise ValueError("图片宽度和高度必须大于 14px")

        total_pixels = width_i * height_i
        if total_pixels < self.CUSTOM_SIZE_MIN_PIXELS or total_pixels > self.CUSTOM_SIZE_MAX_PIXELS:
            raise ValueError(
                f"总像素值(宽*高)必须在[{self.CUSTOM_SIZE_MIN_PIXELS}, "
                f"{self.CUSTOM_SIZE_MAX_PIXELS}]之间"
            )

        ratio = width_i / height_i
        if ratio < 1 / 16 or ratio > 16:
            raise ValueError("图片宽高比必须在[1/16, 16]之间")

        return f"{width_i}x{height_i}"

    @staticmethod
    def _normalize_output_format(output_format: Any) -> str:
        value = output_format or DoubaoSeedream50ProTool.DEFAULT_OUTPUT_FORMAT
        if not isinstance(value, str):
            raise ValueError("output_format must be a string")
        normalized = value.strip().lower()
        if normalized not in {"jpeg", "png"}:
            raise ValueError("output_format must be one of: jpeg, png")
        return normalized

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        credentials = self._get_credentials()
        api_key = (credentials.get("ARK_API_KEY") or credentials.get("ark_api_key") or "").strip()
        if not api_key:
            raise ValueError("Missing provider credential: ARK_API_KEY")

        prompt = tool_parameters.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("请填写提示语")

        image = self._build_images_payload(
            tool_parameters.get("image"),
            tool_parameters.get("image_urls"),
        )
        size = self._normalize_size(tool_parameters)
        output_format = self._normalize_output_format(tool_parameters.get("output_format"))
        watermark = self._coerce_bool(tool_parameters.get("watermark"), default=False)
        base_url = self._normalize_base_url(
            credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url")
        )

        try:
            from volcenginesdkarkruntime import Ark
        except ImportError as e:
            raise RuntimeError(
                "Missing dependency `volcengine-python-sdk[ark]`. "
                "Please ensure it is installed from requirements.txt."
            ) from e

        sdk_kwargs: dict[str, Any] = {
            "model": self.DEFAULT_MODEL,
            "prompt": prompt.strip(),
            "size": size,
            "response_format": "url",
            "watermark": watermark,
            "output_format": output_format,
        }
        if image:
            sdk_kwargs["image"] = image

        client = Ark(api_key=api_key, base_url=base_url)
        response = client.images.generate(**sdk_kwargs)

        data = getattr(response, "data", None)
        if not data:
            raise RuntimeError("生成图片失败")

        result: list[dict[str, str]] = []
        for generated_image in data:
            url = getattr(generated_image, "url", None)
            if url:
                result.append(
                    {
                        "url": str(url),
                        "size": str(getattr(generated_image, "size", "") or ""),
                    }
                )

        if not result:
            raise RuntimeError("生成图片失败")

        markdown_images = "".join(f"![]({generated_image['url']})" for generated_image in result)
        yield self.create_text_message(markdown_images)
        yield self.create_variable_message("images", result)
