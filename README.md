# Antergos NeXT ISO

[![Build ISO](https://github.com/Antergos-NeXT/Antergos-NeXT-ISO/actions/workflows/build.yml/badge.svg)](https://github.com/Antergos-NeXT/Antergos-NeXT-ISO/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Maintenance](https://img.shields.io/maintenance/yes/2026.svg)]()
[![Arch Linux](https://img.shields.io/badge/arch%20linux-rolling-1793d1.svg)](https://archlinux.org)
[![KDE Plasma](https://img.shields.io/badge/DE-KDE%20Plasma-2EA3F2.svg)]()
[![Multi-DE](https://img.shields.io/badge/DE-Cinnamon%20%7C%20XFCE%20%7C%20GNOME%20%7C%20Budgie%20%7C%20Deepin%20%7C%20LXQT%20%7C%20Openbox%20%7C%20i3-ff69b4.svg)]()

Modern revival of the Antergos live installer ISO, based on the maintained EndeavourOS-ISO.

Provides a live KDE Plasma environment to install Arch Linux using **Cnchi**, the original Antergos installer — now patched for modern Python, with multi-DE support and the original installer experience.

## Desktop Editions

| Desktop | Edition | Status |
|---------|---------|--------|
| KDE Plasma | antergos-kde | default |
| GNOME | antergos-gnome | available |
| XFCE | antergos-xfce | available |
| Cinnamon | antergos-cinnamon | available |
| Budgie | antergos-budgie | available |
| Deepin | antergos-deepin | available |
| LXQt | antergos-lxqt | available |
| Openbox | antergos-openbox | available |
| i3 | antergos-i3 | available |
| MATE | antergos-mate | available |

## Download

ISO images exceed GitHub's 2 GB release limit. They are uploaded to [Internet Archive](https://archive.org/details/antergos-next).

**⚠️ Early releases may have incomplete DE package lists.** The latest `packages.xml` is always in the [Cnchi repo](https://github.com/Antergos-NeXT/Cnchi/blob/0.16.x/data/packages.xml). Building from source after a fresh clone ensures you have the most up-to-date package selection.

## How to build

You need an Arch-based system with `archiso` available.

```bash
sudo pacman -S archiso git squashfs-tools --needed
git clone https://github.com/Antergos-NeXT/Antergos-NeXT-ISO.git
cd Antergos-NeXT-ISO
./prepare.sh
sudo ./mkarchiso -v "."
```

The `.iso` appears in the `out/` directory.

## Custom packages

The ISO uses the `antergos-pkgs` repo for custom packages (Cnchi, keyring, mirrorlist, desktop settings, wallpapers). Add it to your system:

```ini
[antergos-pkgs]
SigLevel = Optional TrustAll
Server = https://Antergos-NeXT.github.io/antergos-pkgs/$repo/os/$arch
Server = https://Antergos-NeXT.github.io/antergos-pkgs
```

## Sources

- [EndeavourOS-ISO](https://github.com/endeavouros-team/EndeavourOS-ISO) — base ISO build system
- [Arch-ISO](https://gitlab.archlinux.org/archlinux/archiso) — archiso tools
- [Cnchi](https://github.com/Antergos-NeXT/Cnchi) — our patched Cnchi fork
- [antergos-pkgs](https://github.com/Antergos-NeXT/antergos-pkgs) — custom package repo
- [Antergos wallpapers](https://github.com/Antergos/wallpapers) — original wallpapers

## License

[GPL-3.0](LICENSE)

---

*Antergos launched in 2012 as **Cinnarch** (Cinnamon + Arch), renamed in 2013, and ran until 2019. NeXT revives it KDE first, with the original installer experience and all the desktop choices you remember.*
