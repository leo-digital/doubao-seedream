# 豆包 Seedream Dify 插件

[English](../README.md) | **Simplified Chinese**

[![Version](https://img.shields.io/badge/version-1.2.0-blue)](https://github.com/leo-digital/doubao-seedream)
[![Latest Model](https://img.shields.io/badge/latest-Seedream_5.5-brightgreen)](https://docs.volcengine.com/docs/ark/seedream-5-5?lang=zh)
[![Dify Plugin](https://img.shields.io/badge/Dify-Plugin-orange)](https://dify.ai/)

本项目为 Dify 插件，集成火山引擎豆包 Seedream V4.5、5.0-lite、5.0-pro 与 5.5 模型，带来高质量的 AI 图片生成能力。

## 最新更新

### v1.2.0 — 2026-11-13

- 新增 **图片生成5.5**（`doubao-seedream-5-5-261028`），支持普通生图、透明背景、图层拆分与富文本 OCR。
- 支持 1K/1.5K/2K、最多 10 张参考图；拆分最多输出 100 张图片（包含底图）。

### v1.1.1 - 2026-07-15

- 更新插件的 icon 图标。

### v1.1.0 — 2026-07-10

- 新增 **图片生成 (5.0-pro)** 工具，使用模型 `doubao-seedream-5-0-pro-260628`。
- 支持文生单图、单图参考编辑，以及最多 10 张输入图的多图参考生成。
- 支持 1K/2K 分辨率档位、官方宽高比预设、自定义尺寸，以及 PNG/JPEG 输出。

完整版本历史请查看[更新日志](../docs/zh-CN/CHANGELOG.md)。

## 功能特性

- **文生图**：根据文本描述生成高清图片。
- **图生图**：基于参考图和提示词生成新图片。
- **批量生成**：单次请求可生成多张连贯图片（最多 15 张）。
- **灵活定制**：支持各模型专属分辨率预设和自定义宽高比。
- **高精度生成**：Seedream 5.0-pro 支持单图生成与编辑，最多 10 张参考图。
- **水印控制**：可开关生成图片的水印。

## 可用工具

| Dify 工具 | 模型 ID | 主要能力 | 插件尺寸选项 | 输出格式 |
| :--- | :--- | :--- | :--- | :--- |
| **图片生成 (4.5)** | `doubao-seedream-4-5-251128` | 文生图、图生图、组图生成 | 2K、4K、自定义 | JPEG |
| **图片生成 (5.0-lite)** | `doubao-seedream-5-0-260128` | 文生图、图生图、组图生成、联网搜索 | 2K、3K、自定义 | JPEG、PNG |
| **图片生成 (5.0-pro)** | `doubao-seedream-5-0-pro-260628` | 高精度文生单图、参考图生成 | 1K、2K、自定义 | JPEG、PNG |
| **图片生成5.5** | `doubao-seedream-5-5-261028` | 单图生成/编辑、透明背景、图层拆分、富文本 OCR | 1K、1.5K、2K、自定义；拆分另支持 auto | PNG（默认）、JPEG |

### 参数说明

- prompt：图片生成提示词（支持中英文）。
- sequential_image_generation：设为 True 可生成一组关联图片（最多 15 张）。
- image：图生图任务的参考图片。
- size：多种预设（V4.5：2K/4K；5.0-lite：2K/3K；5.0-pro：1K/2K）、宽高比预设，或 customize 指定具体尺寸。
- width/height：size 设为 customize 时必填。5.0-pro 总像素须在 [921,600, 4,624,220] 内，宽高比须在 1/16 至 16 之间。
- watermark：是否为生成图片添加水印（默认：False）。
- output_format（5.0-lite/5.0-pro）：输出图片格式，jpeg 或 png（默认：jpeg）。
- web_search（5.0-lite）：启用联网搜索工具（由模型决定是否搜索）。

Seedream 5.0-pro 始终返回单张图片，不支持组图生成、联网搜索或流式输出。

## Seedream 5.5 使用方式

在工作流中添加 **图片生成5.5**，复用已有 Ark 凭据。

- **生图与编辑**：填写提示词，可通过 `image` 或 `image_urls` 添加最多 10 张参考图。支持 1K、1.5K、2K（默认）和自定义尺寸。
- **图层拆分**：设置 `layer_decomposition=true`，传入一张 PNG/JPEG，提示词可留空。`max_images` 可设为 2–100（默认 30，含底图）；开启 `text_recognition` 可识别文字及样式。

**示例**

- 透明贴纸：提示词“咖啡杯贴纸”，设置 `background=transparent`、`output_format=png`。
- 海报拆分与 OCR：上传一张海报，设置 `layer_decomposition=true`、`text_recognition=true`。

默认输出 PNG，不加水印。拆分尺寸 `layer_size` 默认为 `auto`，图层始终为 PNG。

结果包含图片预览和 `images` 数组，提供图片 URL、尺寸及可用的图层/OCR 信息。5.5 不支持组图生成、联网搜索或流式输出。

更多参数见 [5.5 教程](https://docs.volcengine.com/docs/ark/seedream-5-5?lang=zh)和 [API 文档](https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh)。

## 安装

### Dify 用户

使用本插件需在 Dify 插件设置中配置以下凭据：

1. 进入 Dify 控制台的**插件**页面。
2. 点击**从 GitHub 安装**或上传插件包。
3. **Ark API Key**：从[火山方舟控制台](https://console.volcengine.com/ark)获取的 API 密钥。
4. **Ark Base URL**：默认为 `https://ark.cn-beijing.volces.com/api/v3`。

### 开发者

如需修改插件，请确保安装以下依赖：

```bash
pip install -r requirements.txt
```

## 重要说明

- **图片有效期**：生成图片的 URL 通常有效期为 **24 小时**。
- **尺寸限制**：自定义尺寸时，宽高比须在 1/16 至 16 之间。

## 隐私政策

本项目隐私条款见 [PRIVACY.md](PRIVACY.md)。
