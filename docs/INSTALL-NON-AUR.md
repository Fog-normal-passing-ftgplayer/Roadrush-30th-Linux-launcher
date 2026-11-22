# 不通过 AUR 的三种安装方式

> AUR 的**新账号注册**在 2026 年这一波自动化注册攻击期间被临时关闭（站点级措施，与你/网络无关）。
> 已有关闭公告：`New account registration is temporarily closed`。开放时间看
> [aur-general](https://lists.archlinux.org/mailman3/lists/aur-general.lists.archlinux.org/)
> 与 [Arch news](https://archlinux.org/news/)；**不要写脚本重试**，页面不会提前告你。
> 下面三种方式都不需要 AUR 账号。

## 方式 1：本地编译安装（最省事，一条命令）
```bash
git clone https://github.com/Fog-normal-passing-ftgplayer/Roadrush-30th-Linux-launcher.git
cd Roadrush-30th-Linux-launcher/packaging/aur
makepkg -si          # 自动装 python-gobject / gtk4 等依赖
```

## 方式 2：自己的 pacman 源（"一键"体验，无需 AUR）
把构建产物传到 GitHub Releases 后，任何人都能一行装：

```bash
# 1) 本机构建产物
packaging/make-release.sh            # 产出 dist/*.pkg.tar.zst + roadrush.db.tar.gz
# 2) 手动上传 dist/ 里三个文件到一个 Release（或 gh release create v0.1.0 dist/*）

# 3) 用户侧：/etc/pacman.conf 追加
[roadrush]
SigLevel = Optional TrustAll
Server = https://github.com/Fog-normal-passing-ftgplayer/Roadrush-30th-Linux-launcher/releases/latest/download

# 4) 安装
sudo pacman -Sy && sudo pacman -S roadrush-launcher-git
```

## 方式 3：免 root 用户级安装（不碰系统目录）
```bash
git clone https://github.com/Fog-normal-passing-ftgplayer/Roadrush-30th-Linux-launcher.git
cd Roadrush-30th-Linux-launcher
./install.sh          # 写入 ~/.local/share/applications + ~/.local/share/icons
python3 gui.py        # 或从应用菜单启动
```

## 依赖（三种方式通用）
| 必需 | 说明 |
|---|---|
| `python` `python-gobject` `gtk4` | GUI |
| 可选 `fluidsynth` `soundfont-fluid` | MIDI 软音源（`Game music` 用） |
| 可选 `ffmpeg` | 音乐槽位转换（8/16-bit RRA） |
| 可选 `steam`（Proton）/ `wine` | 运行环境，启动器首次运行会自动扫描 |

## AUR 开放后
```bash
git clone ssh://aur@aur.archlinux.org/roadrush-launcher-git.git
cd roadrush-launcher-git
cp <repo>/packaging/aur/{PKGBUILD,roadrush-launcher-git.install,.SRCINFO} .
git add -A && git commit -m "Initial import: roadrush-launcher-git" && git push
```
（需要先把 SSH 公钥加到 AUR 账户；`~/.ssh/config` 里给 `aur.archlinux.org` 配 443 端口可绕过 22 端口封锁。）
