from dify_plugin import Tool  # Initialize gevent before HTTP libraries.
from dify_plugin.entities.tool import ToolRuntime

import base64
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import httpx
import yaml
from volcenginesdkarkruntime import Ark

from tools.createimage_sr_55 import DoubaoSeedream55Tool


class Seedream55Tests(unittest.TestCase):
    def setUp(self):
        self.tool = DoubaoSeedream55Tool(
            runtime=ToolRuntime(credentials={"ark_api_key": "test-key"}, user_id=None, session_id=None),
            session=Mock(),
        )
        self.requests = []
        self.emitted = []

    def invoke(self, parameters, data=None, status=200, payload=None):
        if payload is None:
            payload = {
                "model": self.tool.DEFAULT_MODEL,
                "created": 1794500000,
                "data": data if data is not None else [{"url": "https://example.com/result.png", "size": "2048x2048"}],
                "usage": {"generated_images": 1, "output_tokens": 1, "total_tokens": 1},
            }

        def handle(request):
            self.requests.append(request)
            return httpx.Response(status, json=payload)

        def client(**kwargs):
            return Ark(**kwargs, max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handle)))

        with patch("volcenginesdkarkruntime.Ark", side_effect=client):
            self.emitted = []
            for message in self.tool._invoke(parameters):
                self.emitted.append(message)
            return self.emitted

    def body(self):
        return json.loads(self.requests[-1].content)

    def test_generation_defaults_and_output(self):
        messages = self.invoke({"prompt": "  a cat  "})
        body = self.body()
        self.assertEqual(body["model"], "doubao-seedream-5-5-261028")
        self.assertEqual(body["prompt"], "a cat")
        self.assertEqual(body["size"], "2K")
        self.assertEqual(body["output_format"], "png")
        self.assertEqual(body["background"], "auto")
        self.assertEqual(body["response_format"], "url")
        self.assertFalse(body["watermark"])
        for field in ["sequential_image_generation", "stream", "tools", "layer_decomposition_options"]:
            self.assertIsNone(body.get(field))
        self.assertEqual(messages[1].message.variable_name, "images")
        self.assertEqual(messages[1].message.variable_value[0]["url"], "https://example.com/result.png")
        self.assertIn("![](https://example.com/result.png)", messages[0].message.text)

    def test_transparent_and_reference_limit(self):
        urls = ",".join(f"https://example.com/{i}.png" for i in range(10))
        self.invoke({"prompt": "stickers", "background": "transparent", "image_urls": urls})
        self.assertEqual(self.body()["background"], "transparent")
        self.assertEqual(len(self.body()["image"]), 10)
        with self.assertRaises(ValueError):
            self.invoke({"prompt": "stickers", "image_urls": urls + ",https://example.com/extra.png"})

    def test_file_download_and_mixed_references(self):
        file = SimpleNamespace(url="https://dify.example.com/input", mime_type="image/PNG")
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [b"test-image"]
        with patch("tools.createimage_sr_55.requests.get", return_value=response) as get:
            self.invoke({"prompt": "edit", "image": [file], "image_urls": " https://example.com/a.png，https://example.com/b.png "})
        get.assert_called_once_with(file.url, timeout=30, stream=True)
        self.assertEqual(self.body()["image"], ["data:image/png;base64," + base64.b64encode(b"test-image").decode(), "https://example.com/a.png", "https://example.com/b.png"])

    def test_invalid_parameters_fail_before_network(self):
        file = SimpleNamespace(url="https://example.com/input.png", mime_type="image/png")
        cases = [
            {"prompt": ""}, {"background": "transparent", "output_format": "jpeg"},
            {"size": "4K"}, {"size": "customize", "width": 2048.5, "height": 2048},
            {"size": "customize", "width": 0, "height": 2048},
            {"size": "customize", "width": True, "height": 2048},
            {"size": "customize", "width": float("nan"), "height": 2048},
            {"size": "customize", "height": 2048},
            {"size": "customize", "width": 512, "height": 512},
            {"size": "customize", "width": 4096, "height": 4096},
            {"size": "customize", "width": 10000, "height": 100},
            {"layer_decomposition": True, "max_images": 1},
            {"layer_decomposition": True, "max_images": 101},
            {"layer_decomposition": True, "max_images": 2.5},
            {"layer_decomposition": True, "layer_size": "2048x2048"},
            {"layer_decomposition": True, "image_urls": "https://example.com/second.png"},
            {"layer_decomposition": "invalid"}, {"image_urls": "file:///tmp/image.png"},
        ]
        for case in cases:
            with self.subTest(case=case), patch("tools.createimage_sr_55.requests.get") as get:
                with self.assertRaises(ValueError):
                    self.invoke({"prompt": "edit", "image": [file], **case})
                get.assert_not_called()
        self.assertEqual(self.requests, [])

    def test_custom_dimensions_and_all_presets(self):
        for width, height in [(1280, 720), (2140, 2160), (3840, 240), (240, 3840), (2048.0, "2048")]:
            with self.subTest(width=width, height=height):
                self.invoke({"prompt": "test", "size": "customize", "width": width, "height": height})
                self.assertEqual(self.body()["size"], f"{int(width)}x{int(height)}")
        for size in self.tool.SUPPORTED_SIZES:
            with self.subTest(size=size):
                self.invoke({"prompt": "test", "size": size})
                self.assertEqual(self.body()["size"], size)

    def test_decomposition_defaults_and_mode_isolation(self):
        self.invoke({"layer_decomposition": True, "image_urls": "https://example.com/input.png", "size": "customize", "background": "transparent", "output_format": "jpeg"})
        body = self.body()
        self.assertTrue(body["layer_decomposition"])
        self.assertEqual(body["prompt"], "")
        self.assertEqual(body["image"], "https://example.com/input.png")
        self.assertEqual(body["size"], "auto")
        self.assertNotIn("background", body)
        self.assertEqual(body["layer_decomposition_options"], {"max_images": 30, "text_recognition": False})
        for maximum in [2, 100]:
            self.invoke({"layer_decomposition": True, "image_urls": "https://example.com/input.png", "max_images": maximum, "layer_size": "1.5K", "text_recognition": True})
            self.assertEqual(self.body()["layer_decomposition_options"], {"max_images": maximum, "text_recognition": True})
            self.assertEqual(self.body()["size"], "1.5K")
        with self.assertRaises(ValueError):
            self.invoke({"layer_decomposition": True})

    def test_layer_metadata_ocr_and_no_ocr_preserved(self):
        box = {"absolute": [10, 20, 100, 200], "normalized": [5, 10, 50, 100]}
        style = {"similar_font_family": "Arial", "foreground_color": "#123456", "bold": True, "italic": False, "underline": False, "strikethrough": False, "shadow": True, "translucent": True}
        data = [
            {"url": "https://example.com/base.jpg", "size": "2048x2048", "z_index": 0, "output_format": "jpeg", "background": "opaque", "name": "base", "description": "background"},
            {"url": "https://example.com/text.png", "size": "1024x1024", "z_index": 1, "output_format": "png", "background": "transparent", "bounding_box": box, "text_recognition": {"text": "Hello", "lines": [{"bounding_box": box, "runs": [{"text": "Hello", "style": style}]}]}},
        ]
        messages = self.invoke({"layer_decomposition": True, "image_urls": "https://example.com/input.png", "text_recognition": True}, data=data)
        self.assertEqual(messages[1].message.variable_value, data)

    def test_response_failures_never_yield_partial_results(self):
        for data in [[], [{}], [{"url": "https://example.com/ok.png"}, {"error": {"code": "Failed"}}]]:
            with self.subTest(data=data):
                with self.assertRaises(RuntimeError):
                    self.invoke({"layer_decomposition": True, "image_urls": "https://example.com/input.png"}, data=data)
                self.assertEqual(self.emitted, [])
        with self.assertRaises(RuntimeError):
            self.invoke({"prompt": "test"}, payload={"error": {"code": "Failed", "message": "bad"}})
        with self.assertRaises(Exception) as error:
            self.invoke({"prompt": "test"}, status=401, payload={"error": {"code": "Unauthorized", "message": "invalid key"}})
        self.assertIn("401", str(error.exception))

    def test_invalid_files_and_combined_limit_before_download(self):
        valid = SimpleNamespace(url="https://example.com/input.png", mime_type="image/png")
        cases = [
            {"image": "not-a-list"}, {"image": [None, valid]},
            {"image": [SimpleNamespace(url=None, mime_type="image/png")]},
            {"image": [SimpleNamespace(url=valid.url, mime_type="application/pdf")]},
            {"image": [valid], "image_urls": ",".join([valid.url] * 10)},
            {"layer_decomposition": True, "image": [valid, valid]},
            {"layer_decomposition": True, "image": [SimpleNamespace(url=valid.url, mime_type="image/webp")]},
        ]
        for case in cases:
            with self.subTest(case=case), patch("tools.createimage_sr_55.requests.get") as get:
                with self.assertRaises(ValueError):
                    self.invoke({"prompt": "test", **case})
                get.assert_not_called()
        self.assertEqual(self.requests, [])

    def test_empty_or_oversized_file_fails_before_api_call(self):
        file = SimpleNamespace(url="https://example.com/input.png", mime_type="image/png")
        for chunks in [[], [b"123", b"456"]]:
            with self.subTest(chunks=chunks):
                response = Mock()
                response.__enter__ = Mock(return_value=response)
                response.__exit__ = Mock(return_value=False)
                response.iter_content.return_value = chunks
                with patch("tools.createimage_sr_55.requests.get", return_value=response), patch.object(self.tool, "MAX_FILE_BYTES", 5):
                    with self.assertRaises(ValueError):
                        self.invoke({"prompt": "test", "image": [file]})
        self.assertEqual(self.requests, [])

    def test_credentials_and_base_url(self):
        self.tool.runtime.credentials = {"ARK_API_KEY": "test-key", "ARK_BASE_URL": "https://proxy.example.com/api/v3/"}
        self.invoke({"prompt": "test"})
        self.assertEqual(str(self.requests[-1].url), "https://proxy.example.com/api/v3/images/generations")
        self.assertEqual(self.requests[-1].headers["Authorization"], "Bearer test-key")
        self.tool.runtime.credentials = {}
        with self.assertRaisesRegex(ValueError, "ARK_API_KEY"):
            self.invoke({"prompt": "test"})

    def test_provider_loads_all_tools_and_schema_matches(self):
        from dify_plugin.config.config import DifyPluginEnv
        from dify_plugin.core.plugin_registration import PluginRegistration

        registration = PluginRegistration(DifyPluginEnv())
        tools = registration.tools_mapping["doubao-seedream"][2]
        self.assertEqual(set(tools), {"ImageGenerations", "ImageGenerations50Lite", "ImageGenerations50Pro", "ImageGenerations55"})
        schema = yaml.safe_load(Path("tools/createimage_sr_55.yaml").read_text())
        size = next(p for p in schema["parameters"] if p["name"] == "size")
        self.assertEqual({o["value"] for o in size["options"]}, self.tool.SUPPORTED_SIZES | {"customize"})
        properties = schema["output_schema"]["properties"]["images"]["items"]["properties"]
        style = properties["text_recognition"]["properties"]["lines"]["items"]["properties"]["runs"]["items"]["properties"]["style"]["properties"]
        self.assertIn("translucent", style)


if __name__ == "__main__":
    unittest.main()
