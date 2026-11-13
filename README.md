# Doubao Seedream Plugin for Dify

**English** | [Simplified Chinese](readme/README_zh_Hans.md)

[![Version](https://img.shields.io/badge/version-1.2.0-blue)](https://github.com/leo-digital/doubao-seedream)
[![Latest Model](https://img.shields.io/badge/latest-Seedream_5.5-brightgreen)](https://docs.volcengine.com/docs/ark/seedream-5-5?lang=zh)
[![Dify Plugin](https://img.shields.io/badge/Dify-Plugin-orange)](https://dify.ai/)

A Dify plugin that integrates Volcengine's Doubao Seedream V4.5, Seedream 5.0-lite, Seedream 5.0-pro, and Seedream 5.5 models, providing high-quality AI image generation capabilities.

## Latest Updates

### v1.2.0 — 2026-11-13

- Added **ImageGenerations (5.5)** (`doubao-seedream-5-5-261028`) with image generation/editing, transparent backgrounds, layer decomposition and rich-text OCR.
- Supports 1K/1.5K/2K, up to 10 reference images, and up to 100 decomposition outputs including the base image.

### v1.1.1 - 2026-07-15

- Updated the plugin icon.

### v1.1.0 — 2026-07-10

- Added the **ImageGenerations (5.0-pro)** tool using model `doubao-seedream-5-0-pro-260628`.
- Added text-to-single-image, single-reference editing, and multi-reference generation with up to 10 input images.
- Added 1K/2K resolution tiers, official aspect-ratio presets, custom dimensions, and PNG/JPEG output.

See the [full changelog](docs/en-US/CHANGELOG.md) for the complete release history.

## Features

- **Text-to-Image**: Generate high-definition images from text descriptions.
- **Image-to-Image**: Create new images based on a reference image and a prompt.
- **Batch Generation**: Support for generating multiple coherent images (up to 15) in one request.
- **Flexible Customization**: Support for model-specific resolution presets and customizable aspect ratios.
- **High-precision Generation**: Seedream 5.0-pro supports single-image generation and editing with up to 10 reference images.
- **Watermark Control**: Option to toggle watermarks on generated images.

## Available Tools

| Dify Tool | Model ID | Main Capabilities | Plugin Size Options | Output Formats |
| :--- | :--- | :--- | :--- | :--- |
| **ImageGenerations (4.5)** | `doubao-seedream-4-5-251128` | Text-to-image, image-to-image, group generation | 2K, 4K, custom | JPEG |
| **ImageGenerations (5.0-lite)** | `doubao-seedream-5-0-260128` | Text/image generation, group generation, web search | 2K, 3K, custom | JPEG, PNG |
| **ImageGenerations (5.0-pro)** | `doubao-seedream-5-0-pro-260628` | High-precision text-to-single-image and reference-based generation | 1K, 2K, custom | JPEG, PNG |
| **ImageGenerations (5.5)** | `doubao-seedream-5-5-261028` | Single-image generation/editing, transparent backgrounds, layer decomposition, rich-text OCR | 1K, 1.5K, 2K, custom; auto for decomposition | PNG (default), JPEG |

### Parameter Highlights

- prompt: Text prompt to generate an image (Supports Chinese and English).
- sequential_image_generation: Set to True for generating a group of related images (up to 15).
- image: Reference image(s) for Image-to-Image tasks.
- size: Multiple presets (V4.5: 2K/4K; 5.0-lite: 2K/3K; 5.0-pro: 1K/2K), aspect-ratio presets, or customize for specific dimensions.
- width/height: Required when size is set to customize. For 5.0-pro, total pixels must be in [921,600, 4,624,220], with an aspect ratio between 1/16 and 16.
- watermark: Whether to add a watermark to the generated images (Default: False).
- output_format (5.0-lite/5.0-pro): Output image format, jpeg or png (Default: jpeg).
- web_search (5.0-lite): Enable web search tool (the model decides whether to search).

Seedream 5.0-pro always returns a single image and does not support group generation, web search, or streaming output.

## Using Seedream 5.5

Add **ImageGenerations (5.5)** to your workflow with your existing Ark credentials.

- **Generate or edit:** Enter a prompt and optionally add up to 10 reference images through `image` or `image_urls`. Choose 1K, 1.5K, 2K (default), or custom dimensions.
- **Split into layers:** Set `layer_decomposition=true` and provide one PNG/JPEG image. The prompt is optional. Set `max_images` to 2–100 (default 30, including the base image), and enable `text_recognition` for text and style recognition.

**Examples**

- Transparent sticker: prompt “A coffee cup sticker”, `background=transparent`, `output_format=png`.
- Poster layers with OCR: upload one poster, set `layer_decomposition=true` and `text_recognition=true`.

Output defaults to PNG with watermarks off. For decomposition, `layer_size` defaults to `auto`; layers are always PNG.

Results include image previews and an `images` array with URLs, sizes, and available layer/OCR metadata. Seedream 5.5 does not support group generation, web search, or streaming.

See the [5.5 tutorial](https://docs.volcengine.com/docs/ark/seedream-5-5?lang=zh) and [API reference](https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh) for details.

## Installation

### For Dify Users

To use this plugin, you need to configure the following credentials in the Dify plugin settings:
1. Go to **Plugins** in your Dify dashboard.
2. Click on **Install from GitHub** or upload the plugin package.
3. **Ark API Key**: Your API key obtained from the [Volcengine Ark Console](https://console.volcengine.com/ark).
4. **Ark Base URL**: The default is `https://ark.cn-beijing.volces.com/api/v3`.

### For Developers
If you want to modify the plugin, ensure you have the following dependencies:
```bash
pip install -r requirements.txt
```

## Important Notes

- **Image Expiry**: Generated image URLs are typically valid for **24 hours**.
- **Dimension Constraints**: For custom sizes, the aspect ratio must be between 1/16 and 16.

## License

This project is licensed under the terms specified in [PRIVACY.md](PRIVACY.md).
