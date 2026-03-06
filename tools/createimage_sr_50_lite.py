from collections.abc import Generator
from typing import Any

import base64
import json
import logging
import sys

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)


class DoubaoSeedream50LiteTool(Tool):
    DEFAULT_MODEL = "doubao-seedream-5-0-260128"
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

    @classmethod
    def _dump_response_for_log(cls, response: Any) -> dict[str, Any] | str:
        """
        尽量把 SDK 返回对象 dump 成可 JSON 序列化的 dict，便于打印完整响应。
        失败时回退为 str(response)。
        """
        if response is None:
            return {}
        if isinstance(response, dict):
            return response

        dump_fn = getattr(response, "model_dump", None)
        if callable(dump_fn):
            try:
                dumped = dump_fn(mode="json")
                if isinstance(dumped, dict):
                    return dumped
            except TypeError:
                try:
                    dumped = dump_fn()
                    if isinstance(dumped, dict):
                        return dumped
                except Exception:
                    return str(response)
            except Exception:
                return str(response)

        to_dict_fn = getattr(response, "to_dict", None)
        if callable(to_dict_fn):
            try:
                dumped = to_dict_fn()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                return str(response)

        return str(response)

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
        imageUrls = tool_parameters.get('image_urls')  # 图片URL列表
        image = self._build_images_payload(files)
        
        size = self._normalize_size(tool_parameters)
        base_url = self._normalize_base_url(credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url"))

        if imageUrls:
            if isinstance(imageUrls, str):
                # 统一替换中文逗号为半角逗号后分割
                url_list = [u.strip() for u in imageUrls.replace("，", ",").split(",") if u.strip()]
                image.extend(url_list)

        try:
            from volcenginesdkarkruntime import Ark
            from volcenginesdkarkruntime.types.images import ContentGenerationTool
        except ImportError as e:
            raise RuntimeError(
                "Missing dependency `volcengine-python-sdk[ark]`. "
                "Please ensure it is installed from requirements.txt."
            ) from e

        tools: list | None = [ContentGenerationTool(type="web_search")] if web_search else None

        sdk_kwargs: dict[str, Any] = {
            "model": self.DEFAULT_MODEL,
            "prompt": prompt,
            "size": size,
            "sequential_image_generation": sequential_image_generation,
            "response_format": "url",
            "watermark": watermark,
            "output_format": output_format,
        }
        if image:
            sdk_kwargs["image"] = image
        if tools:
            sdk_kwargs["tools"] = tools

        request_body: dict[str, Any] = {
            **sdk_kwargs,
            "tools": [{"type": "web_search"}] if web_search else None,
        }

        client = Ark(api_key=api_key, base_url=base_url)

        def _log(via: str, req: dict[str, Any], resp: Any) -> None:
            sdk_version = None
            try:
                from importlib.metadata import PackageNotFoundError, version

                try:
                    sdk_version = version("volcengine-python-sdk")
                except PackageNotFoundError:
                    sdk_version = None
            except Exception:
                sdk_version = None

            log_req = dict(req)
            if "image" in log_req and isinstance(log_req["image"], list):
                log_req["image"] = [f"<{len(img)} chars>" for img in log_req["image"]]
            resp_dump = self._dump_response_for_log(resp)
            if isinstance(resp_dump, dict):
                if resp_dump.get("created_at") is None:
                    resp_dump.pop("created_at", None)
                if resp_dump.get("tool") is None:
                    resp_dump.pop("tool", None)
            log_obj: dict[str, Any] = {
                "python": sys.version.split()[0],
                "volcengine_python_sdk": sdk_version,
                "base_url": base_url,
                "request": log_req,
                "response": resp_dump,
            }
            msg = json.dumps(
                log_obj,
                ensure_ascii=False,
                separators=(",", ":"),
                default=str,
            )
            logger.info("seedream_5_0_lite.debug %s %s", via, msg)
            print("seedream_5_0_lite.debug", via, msg)

        response = client.images.generate(**sdk_kwargs)

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

        _log("sdk", request_body, response)

        markdown_images = "".join([f"![]({img['url']})" for img in result])
        yield self.create_text_message(markdown_images)
        yield self.create_variable_message("images", result)
