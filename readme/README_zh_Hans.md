# 豆包 Seedream 插件

使用火山引擎（Volcengine）的 **Doubao Seedream V4.5** 模型，实现高质量的图片生成功能。

## 功能特性

- **文生图 (Text-to-Image)**：通过文字描述生成高清图片。
- **图生图 (Image-to-Image)**：支持参考图 + 提示词进行创作。
- **组图生成**：支持一次性生成多张连贯的图片（最多15张）。
- **高度定制**：支持 1K、2K 尺寸，或自定义宽高比。

## 配置指南

在 Dify 插件配置页面，需填写以下凭据：

1.  **Ark API Key**: 从火山引擎方舟控制台获取的 API 密钥。
2.  **Ark Base URL**: 默认为 `https://ark.cn-beijing.volces.com/api/v3`（如有代理请修改）。

## 工具说明

| 工具名称 | 功能描述 | 主要参数 |
| :--- | :--- | :--- |
| **文生图 (Text-to-Image)** | 纯文字生成图片 | `prompt` (必填), `size`, `watermark` |
| **图生图 (Image-to-Image)** | 基于参考图和文字生成 | `prompt`, `image`, `sequential_image_generation` (组图) |
| **创建图片 (Create Image)** | 通用生成接口 | `prompt`, `size`, `model` |

## 注意事项

- 生成的图片 URL 有效期通常为 **24小时**。
- 自定义尺寸需满足总像素在指定范围内且比例在 1/16 到 16 之间。
