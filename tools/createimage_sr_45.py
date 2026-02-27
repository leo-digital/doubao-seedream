from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
# from dify_plugin.file.file import File
from volcenginesdkarkruntime.types.images.images import SequentialImageGenerationOptions
import requests
import base64


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

        generation = tool_parameters.get('sequential_image_generation', False) # 是否生成组图
        prompt = tool_parameters.get('prompt')  # 提示语
        files = tool_parameters.get('image')   # 图片
        size = tool_parameters.get('size', '2K')  # 生成的图片尺寸
        width = tool_parameters.get('width', 1)  # 自定义图片宽度
        height = tool_parameters.get('height', 1)  # 自定义图片高度
        watermark = tool_parameters.get('watermark', False)  # 是否添加水印

        # 如果generation为True, sequential_image_generation这个变量设置为auto, 否则设置为disabled
        sequential_image_generation = "auto" if generation else "disabled"
        
        # 如果prompt为空，就抛出错误
        if not prompt:
            raise ValueError("请填写提示语")
        
        # 如果size的值为customize，就获取width和height的值，将他们相乘，范围要在[3686400, 16777216]之间，width/height的值要在[1/16, 16]之间，否则就抛出错误
        if size == 'customize':
            width = tool_parameters.get('width')
            height = tool_parameters.get('height')
            if not width or not height:
                raise ValueError("请填写图片宽度和高度")
            if width * height < 3686400 or width * height > 16777216:
                raise ValueError("总像素值(宽*高)必须在[3686400, 16777216]之间")
            if width/height < 1/16 or width/height > 16:
                raise ValueError("图片宽高比必须在[1/16, 16]之间")
            size = f"{width}x{height}"

        # 如果files不为空，将files循环读取，读取file中的url和mime_type，然后转为base64，写入image数组中
        # 这里的files如果是空是[None]这样的
        image = []
        # print(f"files: {files}")
        if files and files != [None]:
            for file in files:
                response = requests.get(file.url)
                response.raise_for_status()
                base64_data = base64.b64encode(response.content).decode('utf-8')
            
                # 生成完整的Data URL格式
                data_url = f"data:{file.mime_type};base64,{base64_data}"
                # 将data_url添加到image数组中
                image.append(data_url)

        # print(f"sequential: {sequential_image_generation}")
        # print(f"prompt: {prompt}")
        # print(f"files: {files}")
        # print(f"size: {size}")
        # print(f"width: {width}")
        # print(f"height: {height}")
        # print(f"image: {image}")

        base_url = self._normalize_base_url(credentials.get("ARK_BASE_URL") or credentials.get("ark_base_url"))


        model = self.DEFAULT_MODEL

        # print(f"model: {model}")


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
            image=image,
            size=size,
            sequential_image_generation=sequential_image_generation,
            response_format="url",
            watermark=watermark,
        )

        result = []
        data = getattr(response, "data", None)

        # 判断data是否为空
        if not data:
            raise RuntimeError("生成图片失败")
        else:
            # 判断data是否为列表
            if isinstance(data, list):
                for img in data:
                    result.append({"url": img.url, "size": img.size})

        # 将result数组中的图片url拼接成Markdown格式 ![](url)
        markdown_images = ''.join([f"![]({img['url']})" for img in result])
        yield self.create_text_message(markdown_images)
        yield self.create_variable_message("images", result)
