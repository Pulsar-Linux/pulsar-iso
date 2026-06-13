# Pulsar ISO

[![Build ISO](https://github.com/Pulsar-Linux/pulsar-iso/actions/workflows/build.yml/badge.svg)](https://github.com/Pulsar-Linux/pulsar-iso/actions/workflows/build.yml)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Maintenance](https://img.shields.io/maintenance/yes/2026.svg)]()
[![Arch Linux](https://img.shields.io/badge/arch%20linux-rolling-1793d1.svg)](https://archlinux.org)
[![KDE Plasma](https://img.shields.io/badge/DE-KDE%20Plasma-2EA3F2.svg)]()
[![Multi-DE](https://img.shields.io/badge/DE-Cinnamon%20%7C%20XFCE%20%7C%20GNOME%20%7C%20Budgie%20%7C%20Deepin%20%7C%20LXQT%20%7C%20Openbox%20%7C%20i3-ff69b4.svg)]()

Modern Arch-Based live installer ISO, based on the maintained EndeavourOS-ISO.

Provides a live KDE Plasma environment to install Arch Linux using **Cnchi**, the original Antergos installer that was used all the way to 2019 — now patched for modern Python, with multi-DE support and the original installer experience.

## Desktop Editions

| Desktop | Edition | Status |
|---------|---------|--------|
| KDE Plasma | pulsar-kde | default |
| GNOME | pulsar-gnome | available |
| XFCE | pulsar-xfce | available |
| Cinnamon | pulsar-cinnamon | available |
| Budgie | pulsar-budgie | available |
| Deepin | pulsar-deepin | available |
| LXQt | pulsar-lxqt | available |
| Openbox | pulsar-openbox | available |
| i3 | pulsar-i3 | available |
| MATE | pulsar-mate | available |


## Download

ISO images exceed GitHub's 2 GB release limit. They are uploaded to **SourceForge**
*not ready waiting for new SF account*

**⚠️ Early releases may have incomplete DE package lists.** The latest `packages.xml` is always in the [Cnchi repo](https://github.com/Pulsar-Linux/cnchi/blob/cnchi-dev/data/packages.xml). Building from source after a fresh clone ensures you have the most up-to-date package selection.

## How to build

You need an Arch-based system with `archiso` available.

```bash
sudo pacman -S archiso git squashfs-tools --needed
git clone https://github.com/Pulsar-Linux/pulsar-iso.git
cd pulsar-iso
./prepare.sh
sudo ./mkarchiso -v "."
```

The `.iso` appears in the `out/` directory.

## Custom packages

The ISO uses the `pulsar-pkgs` repo for custom packages (Cnchi, keyring, mirrorlist, desktop settings, wallpapers). Add it to your system:

```ini
[pulsar-pkgs]
SigLevel = Optional TrustAll
Server = https://Pulsar-Linux.github.io/pulsar-pkgs/$repo/os/$arch
Server = https://Pulsar-Linux.github.io/pulsar-pkgs
```

## Sources

- [EndeavourOS-ISO](https://github.com/endeavouros-team/EndeavourOS-ISO) — base ISO build system
- [Arch-ISO](https://gitlab.archlinux.org/archlinux/archiso) — archiso tools
- [Cnchi](https://github.com/Pulsar-Linux/cnchi) — our patched Cnchi fork
- [pulsar-pkgs](https://github.com/Pulsar-Linux/pulsar-pkgs) — custom package repo
- [Pulsar wallpapers](https://github.com/antergos/wallpapers) — original wallpapers (borrowed from Antergos placeholder until i make wallpapers)

## License

[GPL-3.0](LICENSE)
