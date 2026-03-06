# Doubao Seedream Plugin for Dify

[![Version](https://img.shields.io/badge/version-1.0.1-blue)](https://github.com/leo-digital/doubao-seedream)
[![Dify Plugin](https://img.shields.io/badge/Dify-Plugin-orange)](https://dify.ai/)

A Dify plugin that integrates Volcengine's **Doubao Seedream V4.5** and **Seedream 5.0-lite** models, providing high-quality AI image generation capabilities.

## Features

- **Text-to-Image**: Generate high-definition images from text descriptions.
- **Image-to-Image**: Create new images based on a reference image and a prompt.
- **Batch Generation**: Support for generating multiple coherent images (up to 15) in one request.
- **Flexible Customization**: Support for 2K/4K (V4.5) and 2K/3K (5.0-lite) plus customizable aspect ratios.
- **Watermark Control**: Option to toggle watermarks on generated images.

## Configuration

To use this plugin, you need to configure the following credentials in the Dify plugin settings:

1. **Ark API Key**: Your API key obtained from the [Volcengine Ark Console](https://console.volcengine.com/ark).
2. **Ark Base URL**: The default is `https://ark.cn-beijing.volces.com/api/v3`.

## Tool Details

| Tool | Description | Key Parameters |
| :--- | :--- | :--- |
| **ImageGenerations (V4.5)** | General image generation interface | `prompt`, `sequential_image_generation`, `image`, `size`, `watermark` |
| **ImageGenerations (5.0-lite)** | Image generation with PNG & web search | `prompt`, `sequential_image_generation`, `web_search`, `output_format`, `image`, `size`, `watermark` |

### Parameter Highlights:
- `prompt`: Text prompt to generate an image (Supports Chinese and English).
- `sequential_image_generation`: Set to `True` for generating a group of related images (up to 15).
- `image`: Reference image(s) for Image-to-Image tasks.
- `size`: Multiple presets (V4.5: 2K/4K; 5.0-lite: 2K/3K), aspect ratio presets, or `customize` for specific dimensions.
- `width`/`height`: Required when `size` is set to `customize`. Total pixels: V4.5 in [3,686,400, 16,777,216], 5.0-lite in [3,686,400, 10,404,496], with aspect ratio between 1/16 and 16.
- `watermark`: Whether to add a watermark to the generated images (Default: `False`).
- `output_format` (5.0-lite): Output image format, `jpeg` or `png` (Default: `jpeg`).
- `web_search` (5.0-lite): Enable web search tool (the model decides whether to search).

## Installation

### For Dify Users
1. Go to **Plugins** in your Dify dashboard.
2. Click on **Install from GitHub** or upload the plugin package.
3. Configure the `Ark API Key`.

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
