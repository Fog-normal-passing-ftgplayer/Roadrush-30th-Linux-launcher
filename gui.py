#!/usr/bin/env python3
"""ROADRUSH-LINUX-LAUNCHER —— GTK4 图形界面

- 首次启动：扫描系统里的 Wine / Proton，选一个"注册"为运行环境
- 主界面：切换「原版新曲 / 经典 MIDI 曲」、勾选运行选项、一键启动
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import core  # noqa: E402

APP_ID = "io.github.roadrush.Launcher"
CSS = """
.card { background: alpha(currentColor, 0.06); border-radius: 12px; padding: 14px; }
.dim  { opacity: 0.65; }
.mono { font-family: monospace; font-size: 11px; }
.title { font-size: 20px; font-weight: 800; }
.badge-on  { color: #2ec27e; font-weight: 700; }
.badge-off { color: #e5a50a; font-weight: 700; }
"""


def ui(fn):
    """把 fn 丢回 GTK 主线程执行"""
    GLib.idle_add(fn)
    return fn


class Launcher(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.cfg = core.Config.load()
        self.runners: list[core.Runner] = []
        self.game_dirs: list[Path] = []
        self.proc: subprocess.Popen | None = None
        self._loading = False
        self.win: Gtk.ApplicationWindow | None = None

    # ------------------------------------------------------------ 启动 UI
    def do_activate(self):
        if not self.win:
            self.win = Gtk.ApplicationWindow(application=self, title="ROADRUSH-LINUX-LAUNCHER")
            self.win.set_default_size(880, 720)
            self._build()
            self._load_css()
            self._refresh_all()
            if not self.cfg.runner_path or not self.cfg.game_dir:
                self._show_setup()
        self.win.present()

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            self.win.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # -------------------------------------------------------------- 布局
    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16); root.set_margin_bottom(16)
        root.set_margin_start(18); root.set_margin_end(18)
        self.win.set_child(root)

        # 标题
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label="ROADRUSH · LINUX LAUNCHER")
        title.add_css_class("title")
        head.append(title)
        self.lbl_runner_badge = Gtk.Label(label="未配置")
        self.lbl_runner_badge.add_css_class("badge-off")
        head.append(self.lbl_runner_badge)
        root.append(head)

        # 游戏目录
        box_game = self._card("游戏目录")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_game = Gtk.Label(label="（未检测到）")
        self.lbl_game.set_xalign(0); self.lbl_game.set_hexpand(True)
        self.lbl_game.set_ellipsize(3)
        row.append(self.lbl_game)
        b = Gtk.Button(label="浏览…"); b.connect("clicked", self._on_browse_game); row.append(b)
        b = Gtk.Button(label="自动检测"); b.connect("clicked", self._on_autodetect_game); row.append(b)
        box_game.append(row)
        root.append(box_game)

        # 运行环境
        box_run = self._card("运行环境（Wine / Proton）")
        self.dd_runner = Gtk.DropDown.new_from_strings(["（未扫描）"])
        self.dd_runner.connect("notify::selected", self._on_runner_selected)
        box_run.append(self.dd_runner)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        b = Gtk.Button(label="重新扫描"); b.connect("clicked", self._on_rescan); row.append(b)
        self.lbl_runner = Gtk.Label(label=""); self.lbl_runner.add_css_class("dim")
        self.lbl_runner.set_xalign(0); self.lbl_runner.set_ellipsize(3)
        row.append(self.lbl_runner)
        box_run.append(row)
        root.append(box_run)

        # 音乐版本
        box_music = self._card("音乐版本（随时切换，重开游戏生效）")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_old = Gtk.Button(label="应用：经典 MIDI 曲")
        self.btn_new = Gtk.Button(label="应用：30周年纪念版新曲")
        self.btn_old.connect("clicked", lambda *_: self._apply_music("classic"))
        self.btn_new.connect("clicked", lambda *_: self._apply_music("original"))
        row.append(self.btn_old)
        row.append(self.btn_new)
        box_music.append(row)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_gen = Gtk.Button(label="生成经典曲（从游戏文件，约 30 秒）")
        self.btn_gen.connect("clicked", self._on_generate)
        row2.append(self.btn_gen)
        hint = Gtk.Label(label="首次使用：先点这个，本地从你自己的 AUDIO/MUSIC/*.MID 生成")
        hint.add_css_class("dim"); hint.set_xalign(0)
        row2.append(hint)
        box_music.append(row2)

        row3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_preview = Gtk.Button(label="试听 30 秒（经典曲 1）")
        self.btn_preview.connect("clicked", self._on_preview)
        row3.append(self.btn_preview)
        self.lbl_preview = Gtk.Label(label="")
        self.lbl_preview.add_css_class("dim"); self.lbl_preview.set_xalign(0)
        row3.append(self.lbl_preview)
        box_music.append(row3)
        self.lbl_music = Gtk.Label(label="")
        self.lbl_music.add_css_class("dim")
        self.lbl_music.set_xalign(0)
        box_music.append(self.lbl_music)
        root.append(box_music)

        # 选项
        box_opt = self._card("运行选项")
        self.chk_vd = Gtk.CheckButton(label="虚拟桌面模式（解决「卡住要 Alt+Tab 才恢复」/黑屏影片问题）")
        self.chk_vd.set_active(self.cfg.virtual_desktop)
        self.chk_midi = Gtk.CheckButton(label="启动 MIDI 软音源（fluidsynth + ALSA 桥，给 Game music 用）")
        self.chk_midi.set_active(self.cfg.midi_synth)
        self.chk_cars = Gtk.CheckButton(label="有车（取消则把 DATA/CARS 改名，路上不再有车流）")
        self.chk_cars.connect("toggled", self._on_cars_toggle)
        box_opt.append(self.chk_vd)
        box_opt.append(self.chk_midi)
        box_opt.append(self.chk_cars)
        root.append(box_opt)

        # 按钮
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_launch = Gtk.Button(label="▶  启动游戏")
        self.btn_launch.add_css_class("suggested-action")
        self.btn_launch.connect("clicked", self._on_launch)
        self.btn_stop = Gtk.Button(label="■  停止")
        self.btn_stop.connect("clicked", self._on_stop)
        b = Gtk.Button(label="应用设置"); b.connect("clicked", self._on_save)
        row.append(self.btn_launch); row.append(self.btn_stop); row.append(b)
        root.append(row)

        # 日志
        logcard = self._card("日志")
        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(True); sw.set_min_content_height(170)
        self.buf = Gtk.TextBuffer()
        tv = Gtk.TextView(buffer=self.buf)
        tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("mono")
        sw.set_child(tv)
        logcard.append(sw)
        root.append(logcard)

    def _card(self, title: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.add_css_class("card")
        lbl = Gtk.Label(label=title); lbl.set_xalign(0); lbl.add_css_class("dim")
        box.append(lbl)
        return box

    # -------------------------------------------------------------- 日志
    def log(self, msg: str):
        def _do():
            end = self.buf.get_end_iter()
            self.buf.insert(end, msg + "\n")
            tv = self.buf.get_text(self.buf.get_start_iter(), self.buf.get_end_iter(), False)
            if tv.count("\n") > 500:
                self.buf.set_text("\n".join(tv.splitlines()[-400:]) + "\n")
        ui(_do)

    # ------------------------------------------------------------ 状态刷新
    def _refresh_all(self):
        if self.cfg.game_dir:
            self.lbl_game.set_text(self.cfg.game_dir)
        if self.cfg.runner_path:
            self.lbl_runner.set_text(self.cfg.runner_path)
            self.lbl_runner_badge.set_text("已配置")
            self.lbl_runner_badge.remove_css_class("badge-off")
            self.lbl_runner_badge.add_css_class("badge-on")
        self._refresh_music()
        self._sync_cars()
        self._rescan_runners(silent=True)

    MUSIC_LABELS = {"classic": "应用：经典 MIDI 曲", "original": "应用：30周年纪念版新曲"}

    def _style_music(self, mode: str):
        """当前生效的模式：按钮高亮 + ✔ 前缀（色块会跟着变）"""
        for m, btn in (("classic", self.btn_old), ("original", self.btn_new)):
            base = self.MUSIC_LABELS[m]
            if m == mode:
                btn.set_label("✔ " + base)
                btn.add_css_class("suggested-action")
            else:
                btn.set_label(base)
                btn.remove_css_class("suggested-action")

    def _refresh_music(self):
        if not self.cfg.game_dir:
            self.lbl_music.set_text("（未选择游戏目录）")
            self._style_music("")
            return
        st = core.get_music_status(Path(self.cfg.game_dir))
        n_old, n_new = st["classic"], st["original"]
        cur_mode = "classic" if n_old > n_new else "original"
        cur = "经典 MIDI 曲" if cur_mode == "classic" else "30周年纪念版新曲"
        missing = core.classic_sources_missing()
        extra = f" · 经典曲源缺 {len(missing)} 个（点『生成经典曲』）" if missing else ""
        self.lbl_music.set_text(
            f"当前: {cur}   （经典曲 {n_old} 个 / 30周年新曲 {n_new} 个）{extra}")
        self._style_music(cur_mode)

    def _rescan_runners(self, silent=False):
        self._loading = True
        self.runners = core.detect_all_runners()
        labels = [r.label for r in self.runners] or ["（未找到 Wine / Proton）"]
        self.dd_runner.set_model(Gtk.StringList.new(labels))
        idx = 0
        for i, r in enumerate(self.runners):
            if os.path.realpath(r.path) == os.path.realpath(self.cfg.runner_path or ""):
                idx = i
                break
        self.dd_runner.set_selected(idx)
        self._loading = False
        if not silent:
            self.log(f">> 扫描到 {len(self.runners)} 个运行环境")

    # ------------------------------------------------------------ 事件处理
    def _on_rescan(self, _b):
        self._rescan_runners(silent=False)

    def _on_runner_selected(self, dd, _pspec):
        if getattr(self, "_loading", False):
            return
        i = dd.get_selected()
        if 0 <= i < len(self.runners):
            r = self.runners[i]
            self.cfg.runner_type, self.cfg.runner_path = r.kind, r.path
            self.lbl_runner.set_text(r.path)
            self.lbl_runner_badge.set_text("已配置")
            self.lbl_runner_badge.remove_css_class("badge-off")
            self.lbl_runner_badge.add_css_class("badge-on")
            self.cfg.save()
            self.log(f">> 运行环境: {r.kind} → {r.path}")

    def _on_browse_game(self, _b):
        dlg = Gtk.FileChooserNative(title="选择 Road Rash 目录", transient_for=self.win,
                                    action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.connect("response", self._on_browse_response)
        dlg.show()

    def _on_browse_response(self, dlg, resp):
        if resp == Gtk.ResponseType.ACCEPT:
            f = dlg.get_file()
            if f:
                self._set_game_dir(Path(f.get_path()))
        dlg.destroy()

    def _on_autodetect_game(self, _b):
        dirs = core.detect_game_dirs()
        if not dirs:
            self.log("!! 没自动找到，请用「浏览…」手动选")
            return
        self._set_game_dir(dirs[0])
        if len(dirs) > 1:
            self.log(">> 另有: " + ", ".join(str(d) for d in dirs[1:]))

    def _set_game_dir(self, p: Path):
        self.cfg.game_dir = str(p)
        self.cfg.save()
        self.lbl_game.set_text(str(p))
        self.log(f">> 游戏目录: {p}")
        self._refresh_music()
        core.set_cars(p, self.cfg.cars, self.log)
        self._sync_cars()

    def _sync_cars(self):
        self._loading = True
        if self.cfg.game_dir:
            self.chk_cars.set_active(core.get_cars_enabled(Path(self.cfg.game_dir)))
        else:
            self.chk_cars.set_active(self.cfg.cars)
        self._loading = False

    def _on_cars_toggle(self, btn):
        if getattr(self, "_loading", False):
            return
        want = btn.get_active()
        self.cfg.cars = want
        if not self.cfg.game_dir:
            self.cfg.save()
            self.log("!! 先选择游戏目录（已记录偏好，选完目录会自动应用）")
            return
        ok = core.set_cars(Path(self.cfg.game_dir), want, self.log)
        self.cfg.save()
        self.log(f">> {'有车' if want else '无车'}模式：{'已应用（重开游戏生效）' if ok else '应用失败'}")

    def _on_preview(self, _b):
        import subprocess, shutil
        if getattr(self, "_preview_proc", None) and self._preview_proc.poll() is None:
            self._preview_proc.terminate()
            self._preview_proc = None
            self.lbl_preview.set_text("已停止")
            return
        for base in (Path.home() / "Music/roadrush-classic",
                     Path("/tmp/rr-gen-test"),
                     Path(self.cfg.game_dir) / "AUDIO/MUSIC._orig"):
            f = base / "GRUNGE1.flac"
            if f.is_file():
                break
        else:
            self.lbl_preview.set_text("没找到 GRUNGE1.flac（先点『生成经典曲』）")
            return
        player = shutil.which("paplay") or shutil.which("pw-play")
        if not player:
            self.lbl_preview.set_text("缺 paplay/pw-play")
            return
        self._preview_proc = subprocess.Popen(["timeout", "-s", "TERM", "30", player, str(f)],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.lbl_preview.set_text(f"正在播放 30 秒：{f.name}")

    def _on_generate(self, _b):
        if not self.cfg.game_dir:
            self.log("!! 先选择游戏目录")
            return
        self.btn_gen.set_sensitive(False)
        def work():
            try:
                ok = core.generate_classic_music(Path(self.cfg.game_dir), self.log)
                if ok:
                    self.cfg.music_mode = "classic"; self.cfg.save()
            finally:
                ui(lambda: (self.btn_gen.set_sensitive(True), self._refresh_music())[1])
        threading.Thread(target=work, daemon=True).start()

    def _apply_music(self, mode: str):
        if not self.cfg.game_dir:
            self.log("!! 先选择游戏目录")
            return
        label = "经典 MIDI 曲" if mode == "classic" else "30周年纪念版新曲"
        self.log(f">> 切换音乐版本 → {label} …")
        ok = core.apply_music_mode(Path(self.cfg.game_dir), mode, self.log)
        if ok:
            self.cfg.music_mode = mode
            self.cfg.save()
            self.log(">> 切换完成（重开游戏生效）")
        else:
            self.log("!! 切换失败，见上面日志")
            if mode == "classic":
                self.btn_gen.add_css_class("suggested-action")
                self.log(">> 提示：先点上面高亮的「生成经典曲」，~30 秒后再切")
        self._refresh_music()

    def _on_save(self, _b):
        self.cfg.virtual_desktop = self.chk_vd.get_active()
        self.cfg.midi_synth = self.chk_midi.get_active()
        self.cfg.save()
        self.log(">> 设置已保存")

    def _on_launch(self, _b):
        if not self.cfg.runner_path:
            self.log("!! 还没选运行环境")
            self._show_setup()
            return
        if not self.cfg.game_dir:
            self.log("!! 还没选游戏目录")
            return
        self.cfg.virtual_desktop = self.chk_vd.get_active()
        self.cfg.midi_synth = self.chk_midi.get_active()
        self.cfg.cars = self.chk_cars.get_active()
        self.cfg.save()
        core.set_cars(Path(self.cfg.game_dir), self.cfg.cars, self.log)
        self.log("=== 启动游戏 ===")
        self.proc = core.launch(self.cfg, self.log)
        if self.proc:
            threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc: subprocess.Popen):
        try:
            for line in proc.stdout:            # type: ignore[union-attr]
                self.log(line.rstrip())
        except Exception:
            pass
        self.log(f">> 进程结束 (code={proc.poll()})")

    def _on_stop(self, _b):
        core.stop_game()
        self.log(">> 已停止游戏进程")

    # ------------------------------------------------------- 首次运行向导
    def _show_setup(self):
        win = Gtk.Window(transient_for=self.win, modal=True, title="首次运行设置")
        win.set_default_size(760, 520)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(16); box.set_margin_bottom(16)
        box.set_margin_start(16); box.set_margin_end(16)
        win.set_child(box)

        box.append(Gtk.Label(label="① 选择运行环境（检测到的 Wine / Proton）", xalign=0))
        self.setup_runners = core.detect_all_runners()
        labels = [r.label for r in self.setup_runners] or ["（没找到，请先装 Wine 或 Proton）"]
        dd = Gtk.DropDown.new_from_strings(labels)
        # 默认选 GE-Proton（如果有）
        for i, r in enumerate(self.setup_runners):
            if "GE-Proton" in r.label:
                dd.set_selected(i)
                break
        box.append(dd)

        box.append(Gtk.Label(label="② 游戏目录", xalign=0))
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ent = Gtk.Entry()
        found = core.detect_game_dirs()
        ent.set_text(str(found[0]) if found else "")
        ent.set_hexpand(True)
        row.append(ent)
        b = Gtk.Button(label="自动检测")
        b.connect("clicked", lambda *_: ent.set_text(str((core.detect_game_dirs() or [""])[0])))
        row.append(b)
        box.append(row)

        box.append(Gtk.Label(label="③ 音乐版本", xalign=0))
        dd2 = Gtk.DropDown.new_from_strings(["30周年纪念版新曲（默认）", "经典 MIDI 曲（已制作好）"])
        box.append(dd2)

        info = Gtk.Label(label=f"配置将保存到 {core.CONFIG_PATH}", xalign=0)
        info.add_css_class("dim")
        box.append(info)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_halign(Gtk.Align.END)
        ok = Gtk.Button(label="保存并开始")
        ok.add_css_class("suggested-action")

        def _ok(*_):
            i = dd.get_selected()
            if 0 <= i < len(self.setup_runners):
                r = self.setup_runners[i]
                self.cfg.runner_type, self.cfg.runner_path = r.kind, r.path
            if ent.get_text().strip():
                self.cfg.game_dir = ent.get_text().strip()
            mode = "classic" if dd2.get_selected() == 1 else "original"
            self.cfg.music_mode = mode
            self.cfg.save()
            win.close()
            self._refresh_all()
            if self.cfg.game_dir and mode == "classic":
                self.log(">> 应用经典 MIDI 曲 …")
                core.apply_music_mode(Path(self.cfg.game_dir), "classic", self.log)
                self._refresh_music()
            self.log(">> 首次设置完成")

        ok.connect("clicked", _ok)
        row.append(ok)
        box.append(row)
        win.present()


def main() -> int:
    app = Launcher()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
