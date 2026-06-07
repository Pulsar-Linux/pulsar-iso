FROM archlinux:latest

RUN pacman -Syu --noconfirm --needed \
    archiso \
    git \
    squashfs-tools \
    wget \
    imagemagick \
    && pacman -Scc --noconfirm

WORKDIR /build
COPY . .

RUN ./prepare.sh

CMD ["/usr/bin/mkarchiso", "-v", "."]
