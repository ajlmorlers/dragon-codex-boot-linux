# 第三方名称与素材

## Linux 启动器代码

本目录新增的 Linux 启动器代码按 MIT 许可证分发，详见 `LICENSE`。

## 上游项目与原作者

项目名称、默认动画和原始设计来自：

https://github.com/yushua0808-cpu/dragon-codex-boot

- 原作者 / 上游维护者：GitHub [@yushua0808-cpu](https://github.com/yushua0808-cpu)
- 上游版本：v0.2.0
- 上游许可证：MIT License，Copyright (c) 2026 Dragon Codex Boot contributors
- 改编说明：`UPSTREAM.md`

Linux 版独立实现其启动流程的 Linux 替代方案，不包含 Windows WPF/DWM 源码。

## 运行依赖

- GTK 3：LGPL
- PyAV：BSD-3-Clause
- FFmpeg（由 PyAV wheel 提供）：LGPL/GPL，取决于构建选项
- NumPy：BSD-3-Clause
- PulseAudio `paplay` 或 ALSA `aplay`：按系统发行版许可证

这些依赖通过系统包管理器或 Python 环境安装，不修改系统 Python。

## 产品名称与图标

OpenAI、Codex、ChatGPT 和 Linux 名称用于说明所支持的客户端与平台。本项目是独立社区工具，不是官方客户端或官方插件。

Linux 启动器引用系统已安装 ChatGPT 客户端提供的 `chatgpt` 图标主题，不把官方 Logo 文件打包进本仓库或发布包。图标及相关商标权利归其权利人所有。

## 用户媒体和图标

随附演示视频的说明见 `media/MEDIA_NOTICE.md`。用户自行替换的视频、音乐、角色素材和图标，其权利及许可由原提供者规定。
