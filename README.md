# Dragon Codex Boot for Linux（Windows 项目 Linux 改编版）

为 Ubuntu / Linux 桌面提供 Dragon Codex Boot 的原生启动器：全屏播放启动动画和原音轨，随后淡出并打开或唤起 ChatGPT。

> **上游来源与原作者**
>
> 本仓库是根据 [yushua0808-cpu/dragon-codex-boot](https://github.com/yushua0808-cpu/dragon-codex-boot) 的 Windows 版本改编而成的 Linux 版本。原作者与上游维护者为 GitHub 用户 **[@yushua0808-cpu](https://github.com/yushua0808-cpu)**（Dragon Codex Boot maintainers）。
>
> 上游项目提供 Windows WPF/DWM 和 macOS 实现；本仓库新增的是 Linux GTK 3 + PyAV 启动器、安装脚本和桌面集成。Windows 的真实窗口嵌入效果没有移植到 Linux。本项目不是 OpenAI 官方产品，也不隶属于上游项目或 OpenAI。
>
> 详细的改编来源、版本、修改范围和许可见 [UPSTREAM.md](UPSTREAM.md)。

![Dragon Codex Boot Linux 运行预览](assets/preview.png)

## 功能

- 全屏播放随附的 1920×1080 启动动画和原音轨
- 按 `Esc` 或点击右上角“跳过”立即结束动画
- 动画开始时启动 ChatGPT；结束时再次唤起已有窗口
- 在动画尾部平滑淡出，露出已启动的 ChatGPT
- 独立桌面入口，不修改官方 ChatGPT 文件或快捷方式
- 用户级安装，不需要 root 权限
- 支持自定义视频、时间点、音量、全屏和启动命令
- 单实例锁、媒体时长校验和本地诊断日志

## 系统要求

- Ubuntu 22.04/24.04 或其他带 GTK 3 的 Linux 桌面
- Python 3.10 或更新版本
- `python3-pip`、`python3-gi`、`gir1.2-gtk-3.0`
- PulseAudio 或 PipeWire 的 `paplay`，或 ALSA 的 `aplay`
- 已安装 Linux 版 ChatGPT 客户端，命令通常为 `chatgpt`

Ubuntu 如缺组件，可使用：

```bash
sudo apt install python3-pip python3-gi gir1.2-gtk-3.0 pulseaudio-utils
```

PyAV 和 NumPy 会安装到程序目录内的 `python-packages/`，不会修改系统 Python。首次安装需要联网下载 PyAV 二进制包。

如果访问 PyPI 较慢，可以临时指定镜像：

```bash
DRAGON_CODEX_PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ./install.sh
```

## 安装

在项目目录运行：

```bash
./install.sh
```

默认安装位置：

| 内容 | 路径 |
| --- | --- |
| 程序 | `~/.local/share/dragon-codex-boot/` |
| 配置 | `~/.config/dragon-codex-boot/config.json` |
| 命令 | `~/.local/bin/dragon-codex-boot` |
| 桌面入口 | `~/.local/share/applications/dragon-codex-boot.desktop` |
| 日志 | `~/.cache/dragon-codex-boot/last-run.log` |

如果 `~/.local/bin` 不在 `PATH` 中，可使用完整路径启动，或从应用菜单搜索 **Dragon Codex Boot**。

## 使用

从应用菜单打开 **Dragon Codex Boot**，或运行：

```bash
~/.local/bin/dragon-codex-boot
```

动画默认约 14 秒：

- 约 11.3 秒到达原动画的等待节点
- 约 12.7 秒开始淡出
- 约 13.65 秒完成交接
- `Esc` 或右上角按钮可在任意时刻跳过

## 配置

配置文件位于 `~/.config/dragon-codex-boot/config.json`。主要字段：

| 字段 | 说明 |
| --- | --- |
| `Video` | 视频路径；相对路径从程序目录计算 |
| `AppCommand` | ChatGPT 启动命令，例如 `chatgpt` |
| `ActivateCommand` | 结束时用于唤起窗口的命令；留空则复用 `AppCommand` |
| `AppProcessNames` | 等待节点检测的进程名 |
| `HoldAt` | 视频中的客户端等待节点 |
| `TransitionStart` | 开始淡出的时间 |
| `TransitionEnd` | 完成交接的时间 |
| `Volume` | 音量，范围 0–1 |
| `Fullscreen` | 是否全屏播放 |
| `PlayerWidth` / `PlayerHeight` | 非全屏时的窗口尺寸 |
| `SkipFadeSeconds` | 按跳过后的淡出时长 |
| `LaunchTargetAtStart` | 动画开始时是否启动 ChatGPT |
| `ActivateTargetAtEnd` | 结束时是否再次调用启动命令以唤起窗口 |

修改后运行验证：

```bash
~/.local/bin/dragon-codex-boot --verify
```

## 更换动画

1. 将视频复制到 `~/.local/share/dragon-codex-boot/media/startup.mp4`。
2. 根据新视频修改配置中的 `HoldAt`、`TransitionStart` 和 `TransitionEnd`。
3. 运行 `dragon-codex-boot --verify`，确认视频长度超过 `TransitionEnd`。

默认动画播放依赖 PyAV 内置 FFmpeg 解码器。建议使用 H.264/AAC MP4。音频会在首次播放或视频更新后提取为缓存 WAV，后续启动更快。

## 诊断

最近一次运行日志：

```bash
cat ~/.cache/dragon-codex-boot/last-run.log
```

媒体和启动命令检查：

```bash
~/.local/bin/dragon-codex-boot --verify
```

## 卸载

保留个人配置：

```bash
~/.local/share/dragon-codex-boot/uninstall.sh
```

同时删除配置和媒体缓存：

```bash
~/.local/share/dragon-codex-boot/uninstall.sh --purge
```

在源码目录中也可以直接运行 `./uninstall.sh`。

## 与 Windows 版的差异

Linux 版没有 DWM 实时窗口缩略图，因此不会把 ChatGPT 的真实窗口嵌入动画屏幕内。它采用更接近 macOS 版的整窗淡出交接：先启动 ChatGPT，再在动画结尾淡出启动器窗口。

当前使用 GTK 3。GNOME X11 下窗口透明度效果最好；部分 Wayland 合成器可能忽略透明度，但启动和交接仍会继续。启动器不会替换官方 ChatGPT 的桌面文件，也不会设置登录自启。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
./scripts/test.sh
```

## 许可

Linux 启动器源码使用 MIT 许可证。随附演示视频沿用原项目的媒体说明，其许可不自动等同于代码许可证。详情见 `LICENSE`、`THIRD_PARTY_NOTICES.md` 和 `media/MEDIA_NOTICE.md`。
