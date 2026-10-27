#!/usr/bin/env python3
"""Dragon Codex Boot - Linux native startup animation launcher."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import wave
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

APP_ID = "local.dragoncodexboot.linux"
APP_SLUG = "dragon-codex-boot"
VERSION = "1.0.0"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_RELATIVE = Path("config/launcher.json")
warnings.filterwarnings("ignore", message=r".*Gtk\.Window\.(set_wmclass|set_opacity).*")


class ConfigError(ValueError):
    pass


def xdg_path(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    return Path(value).expanduser() if value else fallback


def user_config_path() -> Path:
    return xdg_path("XDG_CONFIG_HOME", Path.home() / ".config") / APP_SLUG / "config.json"


def user_cache_path() -> Path:
    return xdg_path("XDG_CACHE_HOME", Path.home() / ".cache") / APP_SLUG


def user_runtime_path() -> Path:
    value = os.environ.get("XDG_RUNTIME_DIR")
    return Path(value) if value else user_cache_path()


def resolve_config_path(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_config = os.environ.get("DRAGON_CODEX_CONFIG")
    if env_config:
        return Path(env_config).expanduser().resolve()
    installed = user_config_path()
    if installed.is_file():
        return installed
    local = PACKAGE_ROOT / DEFAULT_CONFIG_RELATIVE
    if local.is_file():
        return local
    return PACKAGE_ROOT / "config/launcher.example.json"


def resolve_video_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PACKAGE_ROOT / path
    return path.resolve()


def parse_command(value: Any) -> list[str]:
    if isinstance(value, list):
        command = [str(part) for part in value if str(part)]
    elif isinstance(value, str):
        command = shlex.split(value, posix=True)
    else:
        command = []
    if not command:
        for candidate in ("chatgpt", "codex"):
            if shutil.which(candidate):
                return [candidate]
    return command


@dataclass(frozen=True)
class Config:
    display_name: str
    video: Path
    app_command: list[str]
    activate_command: list[str]
    process_names: tuple[str, ...]
    hold_at: float
    transition_start: float
    transition_end: float
    max_wait_seconds: float
    volume: float
    fullscreen: bool
    player_width: int
    player_height: int
    skip_fade_seconds: float
    launch_target_at_start: bool
    activate_target_at_end: bool

    @classmethod
    def load(cls, path: Path) -> "Config":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigError(f"配置文件不存在：{path}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError(f"配置文件 JSON 格式错误：{exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError("配置文件顶层必须是 JSON 对象。")

        display_name = str(raw.get("DisplayName", "Dragon Codex Boot")).strip()
        video_value = raw.get("Video", "media/startup.mp4")
        if not isinstance(video_value, str) or not video_value.strip():
            raise ConfigError("Video 必须是非空路径。")

        app_command = parse_command(raw.get("AppCommand", "chatgpt"))
        raw_activate_command = raw.get("ActivateCommand")
        activate_command = parse_command(raw_activate_command) if raw_activate_command else list(app_command)
        process_names_raw = raw.get("AppProcessNames", ["chatgpt", "ChatGPT", "codex-launcher"])
        if not isinstance(process_names_raw, list):
            process_names_raw = [process_names_raw]
        process_names = tuple(str(item).strip() for item in process_names_raw if str(item).strip())

        def number(name: str, default: float) -> float:
            try:
                value = float(raw.get(name, default))
            except (TypeError, ValueError) as exc:
                raise ConfigError(f"{name} 必须是数值。") from exc
            if not math.isfinite(value):
                raise ConfigError(f"{name} 必须是有限数值。")
            return value

        def integer(name: str, default: int) -> int:
            value = raw.get(name, default)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ConfigError(f"{name} 必须是整数。")
            return value

        hold_at = number("HoldAt", 11.3)
        transition_start = number("TransitionStart", 12.7)
        transition_end = number("TransitionEnd", 13.65)
        max_wait_seconds = number("MaxWaitSeconds", 60.0)
        volume = number("Volume", 1.0)
        skip_fade_seconds = number("SkipFadeSeconds", 0.25)
        player_width = integer("PlayerWidth", 1280)
        player_height = integer("PlayerHeight", 720)

        if not display_name:
            raise ConfigError("DisplayName 不能为空。")
        if not app_command:
            raise ConfigError("没有找到 AppCommand；请配置 ChatGPT 的启动命令。")
        if not (0 < hold_at < transition_start < transition_end):
            raise ConfigError("请确保 0 < HoldAt < TransitionStart < TransitionEnd。")
        if max_wait_seconds < 1:
            raise ConfigError("MaxWaitSeconds 不能小于 1。")
        if not 0 <= volume <= 1:
            raise ConfigError("Volume 必须在 0 到 1 之间。")
        if not 0.05 <= skip_fade_seconds <= 3:
            raise ConfigError("SkipFadeSeconds 必须在 0.05 到 3 之间。")
        if not (450 <= player_width <= 7680 and 280 <= player_height <= 4320):
            raise ConfigError("PlayerWidth / PlayerHeight 超出支持范围。")

        bools = {}
        for name, default in (
            ("Fullscreen", True),
            ("LaunchTargetAtStart", True),
            ("ActivateTargetAtEnd", True),
        ):
            value = raw.get(name, default)
            if not isinstance(value, bool):
                raise ConfigError(f"{name} 必须是 true 或 false。")
            bools[name] = value

        return cls(
            display_name=display_name,
            video=resolve_video_path(video_value),
            app_command=app_command,
            activate_command=activate_command,
            process_names=process_names,
            hold_at=hold_at,
            transition_start=transition_start,
            transition_end=transition_end,
            max_wait_seconds=max_wait_seconds,
            volume=volume,
            fullscreen=bools["Fullscreen"],
            player_width=player_width,
            player_height=player_height,
            skip_fade_seconds=skip_fade_seconds,
            launch_target_at_start=bools["LaunchTargetAtStart"],
            activate_target_at_end=bools["ActivateTargetAtEnd"],
        )


class Logger:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text("", encoding="utf-8")
        except OSError:
            pass

    def write(self, message: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
        print(f"[DragonCodexBoot] {message}", flush=True)
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
            except OSError:
                pass


class SingleInstance:
    def __init__(self, path: Path):
        self.path = path
        self.handle = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.handle.close()
            self.handle = None
            return False
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(str(os.getpid()))
        self.handle.flush()
        return True

    def release(self) -> None:
        if self.handle is not None:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            finally:
                self.handle.close()
                self.handle = None


def command_exists(command: list[str]) -> bool:
    if not command:
        return False
    executable = command[0]
    if os.path.sep in executable:
        return Path(executable).expanduser().is_file() and os.access(Path(executable).expanduser(), os.X_OK)
    return shutil.which(executable) is not None


def process_running(names: tuple[str, ...]) -> bool:
    wanted = {name.lower() for name in names}
    if not wanted:
        return False
    own_pid = os.getpid()
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit() or int(entry.name) == own_pid:
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip().lower()
            if comm in wanted:
                return True
            raw_cmdline = (entry / "cmdline").read_bytes()
            arguments = [part.decode("utf-8", errors="ignore") for part in raw_cmdline.split(b"\0") if part]
            if any(Path(argument).name.lower() in wanted for argument in arguments[:3]):
                return True
        except (OSError, PermissionError):
            continue
    return False


class MediaError(RuntimeError):
    pass


class MediaBundle:
    def __init__(self, video: Path, cache_dir: Path, logger: Logger):
        self.video = video
        self.cache_dir = cache_dir
        self.logger = logger

    def _audio_cache_path(self) -> Path:
        stat = self.video.stat()
        seed = f"{self.video}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8")
        digest = hashlib.sha256(seed).hexdigest()[:20]
        return self.cache_dir / f"audio-{digest}.wav"

    def prepare_audio(self) -> Optional[Path]:
        if not self.video.is_file():
            raise MediaError(f"启动视频不存在：{self.video}")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        target = self._audio_cache_path()
        if target.is_file() and target.stat().st_size > 44:
            return target

        try:
            import av
        except ImportError as exc:
            raise MediaError("缺少 PyAV 媒体解码库，请重新运行安装脚本。") from exc

        temp = target.with_suffix(".wav.part")
        try:
            with av.open(str(self.video)) as container:
                audio_stream = next(iter(container.streams.audio), None)
                if audio_stream is None:
                    self.logger.write("MEDIA no audio stream")
                    return None
                resampler = av.AudioResampler(format="s16", layout="stereo", rate=48000)
                with wave.open(str(temp), "wb") as output:
                    output.setnchannels(2)
                    output.setsampwidth(2)
                    output.setframerate(48000)
                    frames_written = 0
                    for frame in container.decode(audio_stream):
                        converted = resampler.resample(frame)
                        if converted is None:
                            continue
                        if not isinstance(converted, list):
                            converted = [converted]
                        for item in converted:
                            array = item.to_ndarray()
                            payload = memoryview(array).cast("B").tobytes()
                            output.writeframesraw(payload)
                            frames_written += len(payload)
                    flushed = resampler.resample(None)
                    if flushed is not None:
                        if not isinstance(flushed, list):
                            flushed = [flushed]
                        for item in flushed:
                            array = item.to_ndarray()
                            payload = memoryview(array).cast("B").tobytes()
                            output.writeframesraw(payload)
                            frames_written += len(payload)
            if frames_written <= 0:
                temp.unlink(missing_ok=True)
                self.logger.write("MEDIA audio extraction produced no samples")
                return None
            temp.replace(target)
            self.logger.write(f"MEDIA audio cache ready: {target.name}")
            return target
        except Exception as exc:
            temp.unlink(missing_ok=True)
            raise MediaError(f"音频解码失败：{exc}") from exc

    def verify(self) -> dict[str, Any]:
        if not self.video.is_file():
            raise MediaError(f"启动视频不存在：{self.video}")
        try:
            import av
        except ImportError as exc:
            raise MediaError("缺少 PyAV 媒体解码库，请重新运行安装脚本。") from exc
        try:
            with av.open(str(self.video)) as container:
                video_stream = next(iter(container.streams.video), None)
                if video_stream is None:
                    raise MediaError("视频文件不包含画面轨道。")
                duration = float(container.duration / av.time_base) if container.duration else 0.0
                dimensions = (video_stream.codec_context.width, video_stream.codec_context.height)
                fps = float(video_stream.average_rate) if video_stream.average_rate else 0.0
                first_frame = next(container.decode(video_stream), None)
                if first_frame is None:
                    raise MediaError("无法解码第一帧。")
                audio_stream = next(iter(container.streams.audio), None)
                return {
                    "duration": duration,
                    "width": dimensions[0],
                    "height": dimensions[1],
                    "fps": fps,
                    "audio": audio_stream is not None,
                    "video_codec": video_stream.codec_context.name,
                    "audio_codec": audio_stream.codec_context.name if audio_stream else None,
                }
        except MediaError:
            raise
        except Exception as exc:
            raise MediaError(f"视频验证失败：{exc}") from exc


class LauncherWindow:
    def __init__(self, config: Config, config_path: Path, logger: Logger, options: argparse.Namespace):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            gi.require_version("Gdk", "3.0")
            gi.require_version("GdkPixbuf", "2.0")
            from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
        except (ImportError, ValueError) as exc:
            raise RuntimeError("缺少 GTK 3 Python 组件，请安装 python3-gi 和 gir1.2-gtk-3.0。") from exc

        self.Gdk = Gdk
        self.GdkPixbuf = GdkPixbuf
        self.GLib = GLib
        self.Gtk = Gtk
        GLib.set_prgname(APP_ID)
        self.config = config
        self.config_path = config_path
        self.logger = logger
        self.options = options
        self.origin = 0.0
        self.skip_started_at: Optional[float] = None
        self.finished = False
        self.worker: Optional[threading.Thread] = None
        self.audio_process: Optional[subprocess.Popen[bytes]] = None
        self.stop_event = threading.Event()
        self.frame_lock = threading.Lock()
        self.latest_frame: Optional[Any] = None
        self.frame_idle_pending = False
        self.raw_pixbuf = None
        self.display_size = (config.player_width, config.player_height)
        self.target_launched = False
        self.media_bundle = MediaBundle(config.video, user_cache_path(), logger)

        self.audio_path = self.media_bundle.prepare_audio()
        self.window = Gtk.Window(title=config.display_name)
        self.window.set_wmclass("dragon-codex-boot", config.display_name)
        self.window.set_icon_name("chatgpt")
        icon = None
        for icon_path in (
            Path("/usr/share/pixmaps/chatgpt.png"),
            Path("/usr/local/share/pixmaps/chatgpt.png"),
        ):
            if icon_path.is_file():
                try:
                    icon = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_path), 256, 256, True)
                    break
                except GLib.Error:
                    pass
        if icon is None:
            try:
                icon_theme = Gtk.IconTheme.get_default()
                if icon_theme is not None and icon_theme.has_icon("chatgpt"):
                    icon = icon_theme.load_icon("chatgpt", 256, 0)
            except GLib.Error:
                pass
        if icon is not None:
            self.window.set_icon(icon)
            Gtk.Window.set_default_icon(icon)
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_resizable(config.fullscreen)
        self.window.set_app_paintable(True)
        self.window.connect("key-press-event", self.on_key_press)
        self.window.connect("destroy", self.on_destroy)
        self.window.add_events(Gdk.EventMask.KEY_PRESS_MASK)

        self.drawing_area = Gtk.Image()
        self.drawing_area.set_size_request(config.player_width, config.player_height)
        self.drawing_area.set_hexpand(True)
        self.drawing_area.set_vexpand(True)
        self.drawing_area.connect("size-allocate", self.on_image_size_allocate)

        overlay = Gtk.Overlay()
        overlay.add(self.drawing_area)
        skip_button = Gtk.Button(label="跳过  Esc")
        skip_button.set_halign(Gtk.Align.END)
        skip_button.set_valign(Gtk.Align.START)
        skip_button.set_margin_top(24)
        skip_button.set_margin_end(24)
        skip_button.set_relief(Gtk.ReliefStyle.NONE)
        skip_button.set_can_focus(False)
        skip_button.set_focus_on_click(False)
        skip_button.connect("clicked", lambda _button: self.request_skip("button"))
        skip_button.get_style_context().add_class("skip-button")
        overlay.add_overlay(skip_button)
        self.skip_button = skip_button
        self.window.add(overlay)

        provider = Gtk.CssProvider()
        provider.load_from_data(
            b"""
            window { background: #000; }
            button.skip-button {
              color: rgba(255,255,255,0.86);
              background: rgba(0,0,0,0.46);
              border: 1px solid rgba(255,255,255,0.25);
              border-radius: 18px;
              padding: 7px 16px;
              font-weight: 600;
            }
            button.skip-button:hover { background: rgba(255,255,255,0.16); }
            """
        )
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def show(self) -> None:
        self.window.show_all()
        self.position_window()
        self.window.present()
        self.window.grab_focus()
        self.logger.write(
            f"START version={VERSION} config={self.config_path} video={self.config.video} "
            f"target={' '.join(self.config.app_command)}"
        )
        if self.config.launch_target_at_start and not self.options.no_launch_target:
            self.launch_target(activate=False)
            self.GLib.timeout_add(350, self.raise_window)
            self.GLib.timeout_add(1200, self.raise_window)
        self.GLib.timeout_add(120, self.start_media)

    def raise_window(self) -> bool:
        if self.finished:
            return False
        self.window.present()
        gdk_window = self.window.get_window()
        if gdk_window is not None:
            gdk_window.raise_()
        self.window.grab_focus()
        return False

    def position_window(self) -> None:
        if self.config.fullscreen:
            display = self.Gdk.Display.get_default()
            seat = display.get_default_seat()
            pointer = seat.get_pointer()
            _, x, y = pointer.get_position()
            monitor = display.get_monitor_at_point(x, y)
            monitor_index = 0
            for index in range(display.get_n_monitors()):
                if display.get_monitor(index) == monitor:
                    monitor_index = index
                    break
            self.window.fullscreen_on_monitor(self.Gdk.Screen.get_default(), monitor_index)
            return
        self.window.set_size_request(self.config.player_width, self.config.player_height)
        display = self.Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        _, x, y = pointer.get_position()
        monitor = display.get_monitor_at_point(x, y)
        geometry = monitor.get_geometry()
        width = min(self.config.player_width, geometry.width)
        height = min(self.config.player_height, geometry.height)
        self.window.resize(width, height)
        self.window.move(geometry.x + (geometry.width - width) // 2, geometry.y + (geometry.height - height) // 2)

    def start_media(self) -> bool:
        if self.finished:
            return False
        self.origin = time.monotonic()
        if self.audio_path is not None:
            self.start_audio(self.audio_path)
        self.worker = threading.Thread(target=self.decode_video, name="video-decoder", daemon=True)
        self.worker.start()
        self.GLib.timeout_add(16, self.tick_transition)
        if self.options.test_seconds is not None:
            self.GLib.timeout_add(int(self.options.test_seconds * 1000), self.request_skip, "test_timer")
        return False

    def start_audio(self, path: Path) -> None:
        volume = max(0, min(65536, round(self.config.volume * 65536)))
        paplay = shutil.which("paplay")
        aplay = shutil.which("aplay")
        if paplay:
            command = [paplay, f"--volume={volume}", str(path)]
        elif aplay:
            command = [aplay, "-q", str(path)]
        else:
            self.logger.write("AUDIO no paplay/aplay; continuing without sound")
            return
        try:
            self.audio_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.logger.write(f"AUDIO started via {Path(command[0]).name}")
        except OSError as exc:
            self.logger.write(f"AUDIO start failed: {exc}")

    def launch_target(self, activate: bool) -> bool:
        command = self.config.activate_command if activate else self.config.app_command
        if not command_exists(command):
            self.logger.write(f"TARGET missing command: {' '.join(command)}")
            return False
        try:
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                cwd=str(Path.home()),
            )
            self.target_launched = True
            self.logger.write(f"TARGET {'activate' if activate else 'launch'}: {' '.join(command)}")
            return True
        except OSError as exc:
            self.logger.write(f"TARGET failed: {exc}")
            return False

    def decode_video(self) -> None:
        try:
            import av
            with av.open(str(self.config.video)) as container:
                stream = next(iter(container.streams.video), None)
                if stream is None:
                    raise MediaError("视频没有画面轨道。")
                stream.thread_type = "AUTO"
                first_pts: Optional[float] = None
                paused_for_target = False
                last_frame_time = 0.0
                for frame in container.decode(stream):
                    if self.stop_event.is_set() or self.finished:
                        break
                    if frame.pts is not None:
                        frame_time = float(frame.pts * frame.time_base)
                    else:
                        frame_time = last_frame_time + 1 / 24
                    if first_pts is None:
                        first_pts = frame_time
                    frame_time = max(0.0, frame_time - first_pts)
                    last_frame_time = frame_time

                    if frame_time >= self.config.hold_at and not paused_for_target:
                        paused_for_target = True
                        wait_until = time.monotonic() + self.config.max_wait_seconds
                        if not process_running(self.config.process_names):
                            self.logger.write("TARGET not detected at hold point; waiting")
                            while not self.stop_event.is_set() and time.monotonic() < wait_until:
                                if process_running(self.config.process_names):
                                    break
                                time.sleep(0.05)
                            self.logger.write(
                                "TARGET detected at hold point"
                                if process_running(self.config.process_names)
                                else "TARGET wait timeout; continuing"
                            )

                    target_time = self.origin + frame_time
                    delay = target_time - time.monotonic()
                    if delay > 0:
                        if self.stop_event.wait(delay):
                            break
                    self.queue_frame(frame)
                if not self.stop_event.is_set() and not self.finished:
                    self.logger.write("MEDIA reached end")
                    self.GLib.idle_add(self.request_skip, "media_end")
        except Exception as exc:
            self.logger.write(f"MEDIA decode error: {exc}")
            self.GLib.idle_add(self.show_media_error, str(exc))

    def queue_frame(self, frame: Any) -> None:
        array = frame.to_ndarray(format="rgb24")
        with self.frame_lock:
            self.latest_frame = array
            schedule = not self.frame_idle_pending
            self.frame_idle_pending = True
        if schedule:
            self.GLib.idle_add(self.consume_frame)

    def consume_frame(self) -> bool:
        with self.frame_lock:
            array = self.latest_frame
            self.latest_frame = None
            self.frame_idle_pending = False
        if array is not None:
            height, width, _channels = array.shape
            data = array.tobytes()
            pixbuf = self.GdkPixbuf.Pixbuf.new_from_bytes(
                self.GLib.Bytes.new(data),
                self.GdkPixbuf.Colorspace.RGB,
                False,
                8,
                width,
                height,
                width * 3,
            )
            self.raw_pixbuf = pixbuf
            self.render_pixbuf()
        return False

    def on_image_size_allocate(self, _widget: Any, allocation: Any) -> None:
        size = (max(1, allocation.width), max(1, allocation.height))
        if size != self.display_size:
            self.display_size = size
            self.render_pixbuf()

    def render_pixbuf(self) -> None:
        source = self.raw_pixbuf
        if source is None:
            return
        target_width, target_height = self.display_size
        source_width = source.get_width()
        source_height = source.get_height()
        scale = min(target_width / source_width, target_height / source_height)
        draw_width = max(1, min(target_width, round(source_width * scale)))
        draw_height = max(1, min(target_height, round(source_height * scale)))
        if draw_width == source_width and draw_height == source_height:
            scaled = source
        else:
            scaled = source.scale_simple(draw_width, draw_height, self.GdkPixbuf.InterpType.BILINEAR)
        if draw_width == target_width and draw_height == target_height:
            self.drawing_area.set_from_pixbuf(scaled)
            return
        canvas = self.GdkPixbuf.Pixbuf.new(
            self.GdkPixbuf.Colorspace.RGB, False, 8, target_width, target_height
        )
        canvas.fill(0x000000FF)
        scaled.composite(
            canvas,
            (target_width - draw_width) // 2,
            (target_height - draw_height) // 2,
            draw_width,
            draw_height,
            0,
            0,
            1,
            1,
            self.GdkPixbuf.InterpType.NEAREST,
        )
        self.drawing_area.set_from_pixbuf(canvas)

    def on_key_press(self, _widget: Any, event: Any) -> bool:
        if event.keyval == self.Gdk.KEY_Escape:
            self.request_skip("escape")
            return True
        return False

    def request_skip(self, source: str = "request") -> bool:
        if self.finished:
            return False
        if getattr(self.options, "ignore_input", False) and source in {"button", "escape"}:
            return False
        if self.skip_started_at is None:
            self.skip_started_at = time.monotonic()
            self.logger.write(f"SKIP requested source={source}")
        return False

    def tick_transition(self) -> bool:
        if self.finished:
            return False
        now = time.monotonic()
        opacity = 1.0
        if self.skip_started_at is not None:
            progress = min(1.0, max(0.0, (now - self.skip_started_at) / self.config.skip_fade_seconds))
            opacity = 1.0 - self._smoothstep(progress)
            if progress >= 1.0:
                self.finish()
                return False
        else:
            elapsed = now - self.origin
            if elapsed >= self.config.transition_start:
                progress = min(
                    1.0,
                    max(
                        0.0,
                        (elapsed - self.config.transition_start)
                        / (self.config.transition_end - self.config.transition_start),
                    ),
                )
                opacity = 1.0 - self._smoothstep(progress)
                if progress >= 1.0:
                    self.finish()
                    return False
        try:
            self.window.set_opacity(max(0.0, min(1.0, opacity)))
        except Exception:
            pass
        return True

    @staticmethod
    def _smoothstep(value: float) -> float:
        return value * value * (3.0 - 2.0 * value)

    def show_media_error(self, message: str) -> bool:
        dialog = self.Gtk.MessageDialog(
            transient_for=self.window,
            flags=0,
            message_type=self.Gtk.MessageType.ERROR,
            buttons=self.Gtk.ButtonsType.CLOSE,
            text="无法播放启动动画",
        )
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda d, _r: (d.destroy(), self.finish()))
        dialog.show()
        return False

    def stop_audio(self) -> None:
        process = self.audio_process
        self.audio_process = None
        if process is None or process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=0.4)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
        except OSError:
            pass

    def finish(self) -> bool:
        if self.finished:
            return False
        self.finished = True
        self.stop_event.set()
        self.stop_audio()
        if self.config.activate_target_at_end and not self.options.no_launch_target:
            self.launch_target(activate=True)
        self.logger.write("FINISHED")
        self.GLib.timeout_add(180, self.Gtk.main_quit)
        return False

    def on_destroy(self, *_args: Any) -> None:
        if not self.finished:
            self.finished = True
            self.stop_event.set()
            self.stop_audio()
            self.GLib.idle_add(self.Gtk.main_quit)


def run_verify(config: Config, config_path: Path, logger: Logger) -> int:
    errors = []
    warnings = []
    try:
        bundle = MediaBundle(config.video, user_cache_path(), logger)
        info = bundle.verify()
        bundle.prepare_audio()
        print(json.dumps({"config": str(config_path), "video": str(config.video), **info}, ensure_ascii=False, indent=2))
        if info["duration"] + 0.05 < config.transition_end:
            errors.append(
                f"视频长度 {info['duration']:.2f}s 小于 TransitionEnd {config.transition_end:.2f}s"
            )
        if not info["audio"]:
            warnings.append("视频不包含音频轨道，将静音播放。")
    except (MediaError, OSError) as exc:
        errors.append(str(exc))
    if not command_exists(config.app_command):
        errors.append(f"找不到启动命令：{' '.join(config.app_command)}")
    if not command_exists(config.activate_command):
        warnings.append(f"找不到窗口唤起命令：{' '.join(config.activate_command)}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


def execute(args: argparse.Namespace) -> int:
    config_path = resolve_config_path(args.config)
    cache_dir = user_cache_path()
    logger = Logger(cache_dir / "last-run.log")
    try:
        config = Config.load(config_path)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.verify:
        return run_verify(config, config_path, logger)

    lock = SingleInstance(user_runtime_path() / f"{APP_SLUG}.lock")
    if not lock.acquire():
        print(f"{config.display_name} 已经在运行。", file=sys.stderr)
        return 0
    try:
        if not command_exists(config.app_command) and not args.no_launch_target:
            print(f"ERROR: 找不到 ChatGPT 启动命令：{' '.join(config.app_command)}", file=sys.stderr)
            print("请安装 ChatGPT Linux 客户端，或修改配置中的 AppCommand。", file=sys.stderr)
            return 3
        app = LauncherWindow(config, config_path, logger, args)
        app.show()
        app.Gtk.main()
        return 0
    except (RuntimeError, MediaError, OSError) as exc:
        logger.write(f"FATAL {exc}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    finally:
        lock.release()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dragon Codex Boot Linux launcher")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--verify", action="store_true", help="验证配置、媒体和启动命令")
    parser.add_argument("--no-launch-target", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--test-seconds", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--ignore-input", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
