FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        live-build \
        debootstrap \
        xorriso \
        squashfs-tools \
        isolinux \
        syslinux \
        syslinux-common \
        syslinux-efi \
        grub-pc-bin \
        grub-efi-amd64-bin \
        mtools \
        dosfstools \
        parted \
        e2fsprogs \
        rsync \
        ca-certificates \
        curl \
        wget \
        xz-utils \
        zstd \
        bzip2 \
        gnupg \
        fakeroot \
        uuid-runtime \
        cpio \
        python3 \
        bash \
        file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

ENTRYPOINT ["/bin/bash"]
