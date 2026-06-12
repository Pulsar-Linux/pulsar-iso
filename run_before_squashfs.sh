#!/usr/bin/env bash

# Made by Fernando "maroto"
# Run anything in the filesystem right before being "mksquashed"
# ISO-NEXT specific cleanup removals and additions (08-2021 + 10-2021) @killajoe and @manuel
# refining and changes november 2021 @killajoe and @manuel

script_path=$(readlink -f "${0%/*}")
work_dir="${1:-work}"

# needed for ranking mirrors inside the chroot start
get_country() {
  for url in \
    "https://ipapi.co/country_code" \
    "https://ifconfig.co/country-iso" \
    "https://ipinfo.io/country"; do

    code="$(curl -fs "$url" 2>/dev/null | grep -oE '^[A-Z]{2}$')"
    [[ -n "$code" ]] && echo "$code" && return
  done
}

COUNTRY="$(get_country)"
# needed for ranking mirrors inside the chroot end

# Adapted from AIS. An excellent bit of code!
# all path must be in quotation marks "path/to/file/or/folder" for now.

arch_chroot() {
    local airootfs
    case "${work_dir}" in
        /*) airootfs="${work_dir}/x86_64/airootfs" ;;
        *)  airootfs="${script_path}/${work_dir}/x86_64/airootfs" ;;
    esac
    arch-chroot "${airootfs}" /bin/bash -c "${1}"
}

do_merge() {

arch_chroot "$(cat << EOF

echo "##############################"
echo "# start chrooted commandlist #"
echo "##############################"

cd "/root"

echo "---> Init & Populate keys --->"
pacman-key --init
pacman-key --populate archlinux
echo "---> generating actual ranked mirrorlist to fetch packages for offline install---> "
cp -a "/etc/pacman.d/mirrorlist" "/etc/pacman.d/mirrorlist-from-package"
mkdir -p "/etc/pacman.d/"

echo "---> generate mirrorlist safely ---> "

if [[ -n "$COUNTRY" ]]; then
  reflector \
    --country "$COUNTRY" \
    --protocol "https" \
    --sort "rate" \
    --latest "10" \
    --save "/etc/pacman.d/mirrorlist"
else
  reflector \
    --protocol "https" \
    --sort "rate" \
    --latest "20" \
    --save "/etc/pacman.d/mirrorlist"
fi

echo "---> generate mirrorlist done ---> "
pacman -Syy
echo "---> updating package db done ---> "

echo "---> backup bash configs from skel to replace after antergos creation --->"
mkdir -p "/root/filebackups/"
cp -af "/etc/skel/"{".bashrc",".bash_profile"} "/root/filebackups/"

echo "---> Install antergos skel (in case of conflicts use overwrite) --->"
pacman -U --noconfirm --overwrite "/etc/skel/.bash_profile","/etc/skel/.bashrc" -- "/root/antergos-skel-liveuser/"*".pkg.tar.zst"
echo "---> start validate skel files --->"
ls /etc/skel/.*
ls /etc/skel/
echo "---> end validate skel files --->"

echo "---> Prepare livesession settings and user --->"
sed -i 's/#\(en_US\.UTF-8\)/\1/' "/etc/locale.gen"
locale-gen
ln -sf "/usr/share/zoneinfo/UTC" "/etc/localtime"

echo "---> Set root permission and shell --->"
usermod -s /usr/bin/bash root

echo "---> Create antergos --->"
useradd -m -p "" -g 'antergos' -G 'sys,rfkill,wheel,uucp,nopasswdlogin,adm,tty' -s /bin/bash antergos
if [[ -f "/root/liveuser.png" ]]; then
  cp "/root/liveuser.png" "/var/lib/AccountsService/icons/antergos"
fi

echo "---> Remove antergos skel to clean for target skel --"
pacman -Sy
pacman -Rns --noconfirm -- "antergos-skel-liveuser"
rm -rf "/root/antergos-skel-liveuser"

echo "---> setup theming for root user --->"
cp -a "/root/root-theme" "/root/.config"
rm -R "/root/root-theme"

echo "---> Add Antergos version to motd --->"
echo "Antergos NeXT $(date +%Y.%m.%d)" >> "/etc/motd"
echo "------------------" >> "/etc/motd"

echo "---> Install locally built packages on ISO (place packages under airootfs/root/packages) --->"
echo "--> content of /root/packages:"
if [[ -d "/root/packages/" ]]; then
  ls "/root/packages/"
else
  echo "  (empty - no local packages)"
fi
echo "end of content of /root/packages. <---"

if [[ -d "/root/packages/" ]]; then
  pacman -Sy
  pacman -U --noconfirm --needed -- "/root/packages/"*".pkg.tar.zst"
  rm -rf "/root/packages/"
fi

echo "---> Enable systemd services in case needed --->"
echo " --> per default now in airootfs/etc/systemd/system/multi-user.target.wants"
#systemctl enable NetworkManager.service systemd-timesyncd.service bluetooth.service firewalld.service
#systemctl enable vboxservice.service vmtoolsd.service vmware-vmblock-fuse.service
#systemctl enable intel.service
systemctl set-default multi-user.target

echo "---> Set wallpaper for live-session and installed system --->"
mkdir -p "/usr/share/antergos/backgrounds"
mv "/root/antergos-wallpaper.png" "/usr/share/antergos/backgrounds/antergos-wallpaper.png"
mv "/root/livewall.png" "/usr/share/antergos/backgrounds/antergos-wallpaper-live.png"
chmod 644 "/usr/share/antergos/backgrounds/"*".png"

echo "---> Register wallpaper for Plasma (overwrite default KDE Next/ wallpaper) --->"
for res in 1920x1080 3840x2160 1440x2960 5120x2880 7680x2160; do
  cp "/usr/share/antergos/backgrounds/antergos-wallpaper-live.png" "/usr/share/wallpapers/Next/contents/images/${res}.png"
done

echo "---> Install Antergos icon --->"
mkdir -p "/usr/share/antergos"
if [[ -f "/root/liveuser.png" ]]; then
  cp "/root/liveuser.png" "/usr/share/antergos/antergos-icon.png"
  rm "/root/liveuser.png"
fi

echo "---> install bash configs back into /etc/skel for offline install target --->"
cp -af "/root/filebackups/"{".bashrc",".bash_profile"} "/etc/skel/"

echo "---> remove blacklisting nouveau out of ISO (nvidia-utils blacklist configs) --->"
rm "/usr/lib/modprobe.d/nvidia-utils.conf"
rm "/usr/lib/modules-load.d/nvidia-utils.conf"

echo "---> get needed packages for offline installs --->"
mkdir -p "/usr/share/packages"
pacman -Syy
pacman -Sw --noconfirm --cachedir "/usr/share/packages" grub os-prober xf86-video-intel nvidia-open nvidia-utils broadcom-wl

echo "---> create package versions file --->"
pacman -Qs | grep "/firefox " | cut -c7- > iso_package_versions
pacman -Qs | grep "/linux " | cut -c7- >> iso_package_versions
pacman -Qs | grep "/mesa " | cut -c7- >> iso_package_versions
pacman -Qs | grep "/xorg-server " | cut -c7- >> iso_package_versions
pacman -Qs | grep "/nvidia-utils " | cut -c7- >> iso_package_versions
mv "iso_package_versions" "/home/antergos/"

echo "---> Clean pacman log and package cache --->"
rm "/var/log/pacman.log"
# pacman -Scc seem to fail so:
rm -rf "/var/cache/pacman/pkg/"
echo "---> remove ranked mirrorlist, used for fetching offline packages replacing it with original from package --->"
mv "/etc/pacman.d/mirrorlist-from-package" "/etc/pacman.d/mirrorlist"

echo "---> Fix cnchi desktop file to use pkexec --->"
sed -i 's|^Exec=cnchi$|Exec=pkexec cnchi|' "/usr/share/applications/cnchi.desktop"

echo "---> Set Antergos NeXT os-release --->"
cat > "/usr/lib/os-release" << 'OSEOF'
NAME="Antergos NeXT"
PRETTY_NAME="Antergos NeXT"
ID=antergos
ID_LIKE="arch"
BUILD_ID=rolling
VERSION_ID="rolling"
HOME_URL="https://github.com/Antergos-NeXT"
SUPPORT_URL="https://github.com/Antergos-NeXT"
BUG_REPORT_URL="https://github.com/Antergos-NeXT/issues"
LOGO=antergos-icon
OSEOF

echo "############################"
echo "# end chrooted commandlist #"
echo "############################"

EOF
)"
}

#################################
########## STARTS HERE ##########
#################################

do_merge
