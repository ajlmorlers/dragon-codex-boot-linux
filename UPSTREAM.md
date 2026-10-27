# 上游项目与改编声明

本项目是 **Dragon Codex Boot 的 Linux 改编版本**，不是原始 Windows 项目的官方 Linux 分支。

## 原作者与上游项目

| 项目 | 信息 |
| --- | --- |
| 上游名称 | Dragon Codex Boot |
| 原作者 / 维护者 | GitHub **[@yushua0808-cpu](https://github.com/yushua0808-cpu)**（Dragon Codex Boot maintainers） |
| 上游仓库 | https://github.com/yushua0808-cpu/dragon-codex-boot |
| 使用的发布版 | v0.2.0 |
| 发布版提交 | `d3b7bb84b75134f8250491c86d72996a70d58165` |
| 参考主分支提交 | `c63a203e5857e85fb3c8a9891eddb570e7a27b54` |
| 上游许可证 | MIT License，Copyright (c) 2026 Dragon Codex Boot contributors |

## 本仓库的 Linux 改编内容

Linux 版独立实现了以下部分：

- 使用 GTK 3 创建全屏启动窗口
- 使用 PyAV 解码 H.264 视频和 AAC 音频
- 使用 `paplay` 或 `aplay` 播放原动画音轨
- 实现 `Esc`、跳过按钮、等待节点、淡出和 ChatGPT 交接
- 用户级安装、桌面入口、图标、配置、日志和卸载脚本
- Linux 单实例锁、媒体验证和自动测试

本仓库没有复制或移植 Windows 的 WPF、DWM 实时窗口缩略图和快捷方式替换代码，也不包含 macOS Swift 实现。

## 来源与素材

- 项目创意、启动流程设计、默认时间点配置和随附动画来自上游项目。
- `media/startup.mp4` 为上游项目随附的演示媒体，不属于本仓库代码的 MIT 授权范围。
- 素材使用限制见 [media/MEDIA_NOTICE.md](media/MEDIA_NOTICE.md)。
- 上游项目名称与产品名称说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 许可兼容性

上游代码使用 MIT 许可证。本仓库的 Linux 新增代码也使用 MIT 许可证，并保留上游版权声明。完整文本见 [LICENSE](LICENSE)。

## 非官方声明

OpenAI、Codex、ChatGPT 和相关名称为其各自权利人的商标或产品名称。本项目是独立社区工具，不代表、也不隶属于 OpenAI 或上游项目作者。
