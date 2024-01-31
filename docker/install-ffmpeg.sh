#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}
git clone /tmp/FFmpeg.bundle ffmpeg
cd ffmpeg

PROGRAM_NAME=ffmpeg
VERSION=$(git describe --tags | sed -e 's/^n//')

PKG_ROOT="/tmp/${PROGRAM_NAME}"
mkdir -p "${PKG_ROOT}/usr"

#  --enable-libfaac --enable-gnutls
./configure \
    --prefix="${PKG_ROOT}/usr" \
    --enable-gpl \
    --enable-libfreetype \
    --enable-libmp3lame \
    --enable-libx264 \
    --enable-libx265 \
    --enable-nonfree \
    --enable-openssl \
    --enable-pic \
    --enable-shared \
    --enable-version3 \

make -j4
make install

cd "${PKG_ROOT}"
mkdir DEBIAN
echo Package: "${PROGRAM_NAME}" >> DEBIAN/control
echo Version: "${VERSION}" >> DEBIAN/control
echo Maintainer: fozztexx@fozztexx.com >> DEBIAN/control
echo Architecture: "$(dpkg-architecture -q DEB_HOST_ARCH)" >> DEBIAN/control
#echo Depends: libjansson4, libturbojpeg >> DEBIAN/control
echo Description: "${PROGRAM_NAME}" >> DEBIAN/control

cd ..
dpkg-deb --build "${PKG_ROOT}"

cd
rm -rf ${TMP}
