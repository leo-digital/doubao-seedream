import base64
from collections.abc import Generator
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlsplit

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class DoubaoSeedream55Tool(Tool):
    DEFAULT_MODEL = "doubao-seedream-5-5-261028"
    DEFAULT_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    MAX_REFERENCE_IMAGES = 10
    MAX_FILE_BYTES = 30 * 1024 * 1024
    SIZE_PRESETS = {
        "1K": ("1024x1024", "1152x864", "864x1152", "1424x800", "800x1424", "1248x832", "832x1248", "1568x672"),
        "1.5K": ("1536x1536", "1792x1344", "1344x1792", "2048x1152", "1152x2048", "1872x1248", "1248x1872", "2352x1008"),
        "2K": ("2048x2048", "2368x1776", "1776x2368", "2816x1584", "1584x2816", "2496x1664", "1664x2496", "3136x1344"),
    }
    SUPPORTED_SIZES = set(SIZE_PRESETS) | {size for sizes in SIZE_PRESETS.values() for size in sizes}

    @staticmethod
    def _boolean(value: Any, name: str) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (str, int, float)):
            normalized = str(value).strip().lower()
            if normalized in {"true", "1", "1.0", "yes", "on"}:
                return True
            if normalized in {"false", "0", "0.0", "no", "off"}:
                return False
        raise ValueError(f"{name} 必须为布尔值 / must be a boolean")

    @staticmethod
    def _integer(value: Any, name: str) -> int:
        try:
            number = Decimal(str(value))
            if isinstance(value, bool) or not number.is_finite() or number != number.to_integral_value():
                raise ValueError
            return int(number)
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"{name} 必须为整数 / must be an integer") from exc

    @staticmethod
    def _choice(value: Any, default: str, options: set[str], name: str) -> str:
        value = default if value is None or value == "" else value
        if not isinstance(value, str) or value.strip() not in options:
            raise ValueError(f"{name} 必须为 / must be one of: {', '.join(sorted(options))}")
        return value.strip()

    def _size(self, parameters: dict[str, Any]) -> str:
        size = self._choice(parameters.get("size"), "2K", self.SUPPORTED_SIZES | {"customize"}, "size")
        if size != "customize":
            return size
        width = self._integer(parameters.get("width"), "width")
        height = self._integer(parameters.get("height"), "height")
        if width <= 0 or height <= 0:
            raise ValueError("宽高必须为正整数 / Width and height must be positive")
        if not 921600 <= width * height <= 4624220:
            raise ValueError("总像素（宽×高）必须在 [921600, 4624220] / Invalid pixel count")
        if not 1 / 16 <= width / height <= 16:
            raise ValueError("宽高比必须在 [1/16, 16] / Invalid aspect ratio")
        return f"{width}x{height}"

    @staticmethod
    def _http_url(value: Any, name: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{name} must be an HTTP(S) URL")
        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{name} must be an HTTP(S) URL")
        return value

    def _references(self, parameters: dict[str, Any], layers: bool) -> tuple[list[Any], list[str]]:
        files = parameters.get("image")
        if files is None or files == [None]:
            files = []
        if not isinstance(files, list):
            raise ValueError("image must be a list of files")
        image_urls = parameters.get("image_urls")
        if image_urls is None:
            image_urls = ""
        if not isinstance(image_urls, str):
            raise ValueError("image_urls must be a comma-separated string")
        urls = [self._http_url(url, "image_urls") for url in image_urls.replace("，", ",").split(",") if url.strip()]
        count = len(files) + len(urls)
        if layers and count != 1:
            raise ValueError("图层拆分必须且只能输入一张图片 / Layer decomposition requires exactly one image")
        if count > self.MAX_REFERENCE_IMAGES:
            raise ValueError("参考图最多支持 10 张 / At most 10 reference images")
        formats = {"image/png", "image/jpeg"} if layers else {
            "image/png", "image/jpeg", "image/webp", "image/bmp", "image/tiff", "image/gif", "image/heic", "image/heif",
        }
        for file in files:
            self._http_url(getattr(file, "url", None), "image.url")
            mime = getattr(file, "mime_type", "") or ""
            if mime.lower() not in formats:
                raise ValueError("不支持的参考图格式 / Unsupported reference image format")
        return files, urls

    def _fetch_file(self, file: Any) -> str:
        content = bytearray()
        with requests.get(file.url, timeout=30, stream=True) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > self.MAX_FILE_BYTES:
                    raise ValueError("参考图不能超过 30 MB / Reference image exceeds 30 MB")
        if not content:
            raise ValueError("参考图内容为空 / Empty reference image")
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{file.mime_type.lower()};base64,{encoded}"

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        credentials = self.runtime.credentials
        api_key = (credentials.get("ARK_API_KEY") or credentials.get("ark_api_key") or "").strip()
        if not api_key:
            raise ValueError("Missing provider credential: ARK_API_KEY")
        base_url = self._http_url(
            credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url") or self.DEFAULT_ARK_BASE_URL,
            "ARK_BASE_URL",
        ).rstrip("/")
        layers = self._boolean(tool_parameters.get("layer_decomposition"), "layer_decomposition")
        prompt = tool_parameters.get("prompt")
        if prompt is None:
            prompt = ""
        if not isinstance(prompt, str) or (not layers and not prompt.strip()):
            raise ValueError("请填写文本提示词 / A text prompt is required for image generation")
        output_format = self._choice(tool_parameters.get("output_format"), "png", {"png", "jpeg"}, "output_format")
        watermark = self._boolean(tool_parameters.get("watermark"), "watermark")
        extra_body: dict[str, Any]
        if layers:
            size = self._choice(tool_parameters.get("layer_size"), "auto", {"auto", "1K", "1.5K", "2K"}, "layer_size")
            maximum = tool_parameters.get("max_images")
            max_images = self._integer(30 if maximum is None else maximum, "max_images")
            if not 2 <= max_images <= 100:
                raise ValueError("max_images 必须在 [2, 100] / must be between 2 and 100")
            extra_body = {
                "layer_decomposition": True,
                "layer_decomposition_options": {
                    "max_images": max_images,
                    "text_recognition": self._boolean(tool_parameters.get("text_recognition"), "text_recognition"),
                },
            }
        else:
            size = self._size(tool_parameters)
            background = self._choice(tool_parameters.get("background"), "auto", {"auto", "transparent", "opaque"}, "background")
            if background == "transparent" and output_format != "png":
                raise ValueError("透明背景必须使用 PNG / Transparent background requires PNG")
            extra_body = {"background": background}

        # Validate every local parameter and file descriptor before downloading files.
        files, urls = self._references(tool_parameters, layers)
        images = [self._fetch_file(file) for file in files] + urls

        from volcenginesdkarkruntime import Ark

        kwargs: dict[str, Any] = {
            "model": self.DEFAULT_MODEL,
            "prompt": prompt.strip(),
            "size": size,
            "output_format": output_format,
            "response_format": "url",
            "watermark": watermark,
            "extra_body": extra_body,
        }
        if images:
            kwargs["image"] = images[0] if layers else images
        # Empty prompts in decomposition mean automatic element selection.
        with Ark(api_key=api_key, base_url=base_url) as client:
            response = client.images.generate(**kwargs)
        payload = response.model_dump(mode="json", exclude_none=True)
        if payload.get("error"):
            raise RuntimeError(f"Seedream 5.5 API error: {payload['error']}")
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise RuntimeError("生成图片失败：返回为空 / Empty image response")
        for item in data:
            if not isinstance(item, dict) or item.get("error") or not item.get("url"):
                raise RuntimeError("生成图片失败：存在失败图片或缺少 URL / Failed image or missing URL")
        # Preserve layer coordinates, OCR runs/styles, and future response fields.
        yield self.create_text_message("\n\n".join(f"![]({item['url']})" for item in data))
        yield self.create_variable_message("images", data)
