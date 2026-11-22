"""ROADRUSH-LINUX-LAUNCHER —— 核心逻辑（探测 / 配置 / 音乐切换 / 启动）

不依赖 GUI，可单独用：
    python3 core.py --detect        列出探测到的 wine / Proton / 游戏目录
    python3 core.py --status        当前配置
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "roadrush-launcher"
CONFIG_PATH = CONFIG_DIR / "config.json"

GAME_EXE = "RoadRash95.exe"
DEFAULT_PROTON_PREFIX = Path.home() / ".local/share/road-rash-30th"
MENU_LOCK_SLOT = "HB_TRIP"          # 前端锁定的原版曲（Jukebox 里锁定 HB_Trip）

PROTON_GLOBS = [
    "~/.local/share/Steam/compatibilitytools.d/*/proton",
    "~/.steam/steam/compatibilitytools.d/*/proton",
    "~/.local/share/Steam/steamapps/common/Proton*/proton",
    "~/.steam/steam/steamapps/common/Proton*/proton",
]


# ---------------------------------------------------------------- 配置 ----
@dataclass
class Config:
    game_dir: str = ""
    runner_type: str = ""          # "proton" | "wine"
    runner_path: str = ""          # proton 可执行文件 / wine 可执行文件
    virtual_desktop: bool = True  # 虚拟桌面（解决 Alt+Tab 才恢复/黑屏）
    midi_synth: bool = True       # 起 fluidsynth + ALSA 桥（Game music 用）
    music_mode: str = "classic"   # "classic" | "original"
    reg_done: bool = False

    @classmethod
    def load(cls) -> "Config":
        try:
            raw = json.loads(CONFIG_PATH.read_text())
            known = {f for f in cls.__dataclass_fields__}
            return cls(**{k: v for k, v in raw.items() if k in known})
        except Exception:
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- 探测 ----
@dataclass
class Runner:
    kind: str          # "wine" | "proton"
    path: str
    label: str


def _wine_version(path: str) -> str:
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).strip()
    except Exception:
        return "unknown"


def detect_wine() -> list[Runner]:
    runners: list[Runner] = []
    seen = set()
    for name in ("wine", "wine64", "wine-stable", "wine-staging", "wine64-stable"):
        p = shutil.which(name)
        if not p or os.path.realpath(p) in seen:
            continue
        seen.add(os.path.realpath(p))
        runners.append(Runner("wine", p, f"系统 Wine — {_wine_version(p)} ({p})"))
    for cand in ("/opt/wine-stable/bin/wine", "/opt/wine-staging/bin/wine", "/opt/proton-ge-custom/proton"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK) and os.path.realpath(cand) not in seen:
            seen.add(os.path.realpath(cand))
            runners.append(Runner("proton" if cand.endswith("proton") else "wine", cand, cand))
    return runners


def detect_proton() -> list[Runner]:
    runners: list[Runner] = []
    seen = set()
    for pattern in PROTON_GLOBS:
        for p in sorted(Path.home().glob(pattern.replace("~/", ""))):
            rp = os.path.realpath(p)
            if rp in seen or not os.access(p, os.X_OK):
                continue
            seen.add(rp)
            ver = p.parent.name
            runners.append(Runner("proton", str(p), f"{ver}  ({p})"))
    # 按名字里的版本号粗略排序，新的靠后
    runners.sort(key=lambda r: r.label)
    return runners


def detect_all_runners() -> list[Runner]:
    return detect_proton() + detect_wine()


def _looks_like_game(d: Path) -> bool:
    try:
        return d.is_dir() and (d / GAME_EXE).is_file()
    except OSError:
        return False


def detect_game_dirs() -> list[Path]:
    """在常见位置浅层搜索 RoadRash95.exe"""
    roots = [Path.home(), Path.home() / "Games", Path.home() / "下载",
             Path.home() / "游戏", Path("/media"), Path("/mnt"), Path("/run/media")]
    found: list[Path] = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        try:
            for depth in range(0, 4):
                pattern = "/".join(["*"] * depth) + ("/" if depth else "") + "RoadRash95.exe"
                for exe in root.glob(pattern):
                    d = exe.parent
                    if os.path.realpath(d) not in seen:
                        seen.add(os.path.realpath(d))
                        found.append(d)
                if len(found) > 8:
                    return found
        except OSError:
            continue
    return found


# ------------------------------------------------------------ 音乐切换 ----
def music_mode_script(game_dir: Path) -> Path:
    """游戏目录里优先；也支持 AUR 安装位置 / 源码树里的 tools/"""
    here = Path(__file__).resolve().parent
    for cand in (game_dir / "music-mode.sh",
                 here / "music-mode.sh",
                 here / "tools" / "music-mode.sh",
                 Path("/usr/share/roadrush-launcher/tools/music-mode.sh")):
        if cand.is_file():
            return cand
    return game_dir / "music-mode.sh"


def _tool_script(name: str) -> Path | None:
    here = Path(__file__).resolve().parent
    for cand in (here / name, here / "tools" / name,
                 Path("/usr/share/roadrush-launcher/tools") / name):
        if cand.is_file():
            return cand
    return None


def generate_classic_music(game_dir: Path, log=print, out_dir: Path | None = None) -> bool:
    """从用户自己的游戏文件一键生成经典 MIDI 曲并装入游戏（约 30 秒）"""
    script = _tool_script("make-classic-music.sh")
    if not script:
        log("!! 找不到 make-classic-music.sh")
        return False
    out = out_dir or (Path.home() / "Music/roadrush-classic")
    cmd = ["bash", str(script), "--game", str(game_dir), "--out", str(out), "--install"]
    log(">> 开始生成经典曲（解码 MIDS → 渲染 → 装入游戏）…")
    try:
        env = dict(os.environ, GAME_DIR=str(game_dir))
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
        for line in (p.stdout or "").splitlines():
            log("  " + line)
        if p.returncode != 0:
            for line in (p.stderr or "").splitlines()[-8:]:
                log("  ! " + line)
            log(f"!! 生成失败（退出码 {p.returncode}）")
            return False
        log(">> 生成并装入完成")
        return True
    except Exception as e:                       # noqa: BLE001
        log(f"!! 生成失败: {e}")
        return False


def get_music_status(game_dir: Path) -> dict:
    """返回 {'classic': n, 'original': n, 'menu': slot}"""
    music = game_dir / "AUDIO/MUSIC"
    backup = game_dir / "AUDIO/MUSIC._orig"
    classic = original = 0
    if music.is_dir() and backup.is_dir():
        for f in music.glob("*.RRA"):
            o = backup / f.name
            try:
                if o.is_file() and abs(f.stat().st_size - o.stat().st_size) < 1024:
                    original += 1
                else:
                    classic += 1
            except OSError:
                pass
    return {"classic": classic, "original": original}


def apply_music_mode(game_dir: Path, mode: str, log=print) -> bool:
    script = music_mode_script(game_dir)
    if not script.is_file():
        log(f"!! 找不到 {script}")
        return False
    script.chmod(0o755)
    try:
        env = dict(os.environ, GAME_DIR=str(game_dir))
        p = subprocess.run([str(script), mode], cwd=str(game_dir), env=env, capture_output=True,
                           text=True, timeout=300)
        for line in (p.stdout or "").splitlines():
            log("  " + line)
        if p.returncode != 0:
            log(f"!! music-mode.sh 退出码 {p.returncode}")
            return False
        return True
    except Exception as e:                       # noqa: BLE001
        log(f"!! 切换失败: {e}")
        return False


# -------------------------------------------------------------- 启动 ----
def _reg_add(prefix: Path, wine_bin: str | None, key: str, name: str, value: str) -> None:
    """补安装检测用的注册表键（32 位视图 Wow6432Node）"""
    env = dict(os.environ, WINEPREFIX=str(prefix))
    if wine_bin and Path(wine_bin).is_file():
        cmd = [wine_bin, "reg", "add", key, "/v", name, "/t", "REG_SZ", "/d", value, "/f"]
        subprocess.run(cmd, env=env, capture_output=True, timeout=60)
    elif shutil.which("wine"):
        cmd = ["wine", "reg", "add", key, "/v", name, "/t", "REG_SZ", "/d", value, "/f"]
        subprocess.run(cmd, env=env, capture_output=True, timeout=60)


def ensure_registry(cfg: Config, log=print) -> None:
    game_dir = Path(cfg.game_dir)
    winpath = "Z:" + str(game_dir).replace("/", "\\") + "\\"
    key = r"HKLM\Software\Wow6432Node\Electronic Arts\RoadRash 95"
    if cfg.runner_type == "proton":
        pfx = Path(os.environ.get("STEAM_COMPAT_DATA_PATH", DEFAULT_PROTON_PREFIX)) / "pfx"
        wine_bin = str(Path(cfg.runner_path).parent / "files/bin/wine")
    else:
        pfx = Path.home() / ".wine"
        wine_bin = cfg.runner_path
    if not pfx.is_dir():
        log(">> 前缀还不存在，首次启动时会自动创建并写注册表")
        return
    _reg_add(pfx, wine_bin, key, "path", winpath)
    _reg_add(pfx, wine_bin, key, "language", "English")
    log(">> 注册表检查完成")


def launch(cfg: Config, log=print) -> subprocess.Popen | None:
    game_dir = Path(cfg.game_dir)
    if not _looks_like_game(game_dir):
        log(f"!! {game_dir} 里没有 {GAME_EXE}")
        return None

    env = dict(os.environ)
    env["WINEDLLOVERRIDES"] = "dxva2=d" + (";" + env["WINEDLLOVERRIDES"] if env.get("WINEDLLOVERRIDES") else "")
    # 去掉输入法尾巴，避免全屏 DD 游戏丢焦点
    for k in ("XMODIFIERS", "XIM", "XIM_PROGRAM", "XIM_ARGS"):
        env.pop(k, None)
    env.update(GTK_IM_MODULE="none", QT_IM_MODULE="none", SDL_IM_MODULE="none")

    ensure_registry(cfg, log)

    if cfg.runner_type == "proton":
        proton = cfg.runner_path
        env["STEAM_COMPAT_DATA_PATH"] = str(Path(os.environ.get("STEAM_COMPAT_DATA_PATH", DEFAULT_PROTON_PREFIX)))
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(Path.home() / ".steam/steam")
        Path(env["STEAM_COMPAT_DATA_PATH"]).mkdir(parents=True, exist_ok=True)
        if cfg.midi_synth:
            start_midi_synth(log)
        if cfg.virtual_desktop:
            win_exe = "Z:" + str(game_dir).replace("/", "\\") + "\\" + GAME_EXE
            cmd = [proton, "run", "explorer", "/desktop=RoadRash,1920x1080", win_exe]
        else:
            cmd = [proton, "run", GAME_EXE]
    else:
        wine = cfg.runner_path or "wine"
        env.setdefault("WINEPREFIX", str(Path.home() / ".wine"))
        if cfg.virtual_desktop:
            cmd = [wine, "explorer", "/desktop=RoadRash,1920x1080", GAME_EXE]
        else:
            cmd = [wine, GAME_EXE]

    log(">> " + " ".join(cmd))
    try:
        return subprocess.Popen(cmd, cwd=str(game_dir), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, start_new_session=True)
    except Exception as e:                       # noqa: BLE001
        log(f"!! 启动失败: {e}")
        return None


def start_midi_synth(log=print) -> None:
    bridge = Path.home() / ".local/share/road-rash-30th/bin/seq-connect"
    sf = "/usr/share/soundfonts/FluidR3_GM.sf2"
    if not shutil.which("fluidsynth") or not Path(sf).is_file():
        log(">> [MIDI] 缺 fluidsynth 或音色库，跳过")
        return
    try:
        if not subprocess.run(["pgrep", "-x", "fluidsynth"], capture_output=True).returncode == 0:
            subprocess.Popen(
                ["bash", "-c", f"tail -f /dev/null | exec fluidsynth -a pulseaudio -m alsa_seq -g 1.0 '{sf}'"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            log(">> [MIDI] fluidsynth 已启动")
        if bridge.is_file() and subprocess.run(["pgrep", "-x", "seq-connect"], capture_output=True).returncode != 0:
            subprocess.Popen([str(bridge)], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            log(">> [MIDI] ALSA 桥已启动")
    except Exception as e:                       # noqa: BLE001
        log(f">> [MIDI] 启动失败: {e}")


def stop_game() -> None:
    subprocess.run(["pkill", "-x", "RoadRash95.exe"], capture_output=True)


# -------------------------------------------------------------- CLI ----
def _cli() -> int:
    if "--detect" in sys.argv:
        print("== Proton ==")
        for r in detect_proton():
            print("  ", r.label)
        print("== Wine ==")
        for r in detect_wine():
            print("  ", r.label)
        print("== 游戏目录 ==")
        for d in detect_game_dirs():
            print("  ", d)
        return 0
    if "--status" in sys.argv:
        cfg = Config.load()
        print(json.dumps(asdict(cfg), indent=2, ensure_ascii=False))
        if cfg.game_dir:
            print("音乐:", get_music_status(Path(cfg.game_dir)))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
