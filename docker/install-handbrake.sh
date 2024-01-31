#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}
#git clone https://github.com/HandBrake/HandBrake
git clone /tmp/HandBrake.bundle

cd HandBrake
#export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig/

PROGRAM_NAME=handbrake
VERSION=$(git describe --tags)

PKG_ROOT="/tmp/${PROGRAM_NAME}"
mkdir -p "${PKG_ROOT}/usr"

echo Configuring
./configure --disable-gtk --launch --prefix="${PKG_ROOT}/usr"
make --directory=build install

cd "${PKG_ROOT}"
mkdir DEBIAN
echo Package: "${PROGRAM_NAME}" >> DEBIAN/control
echo Version: "${VERSION}" >> DEBIAN/control
grep Maintainer: ${TMP}/HandBrake/pkg/linux/debian/control >> DEBIAN/control
echo Architecture: "$(dpkg-architecture -q DEB_HOST_ARCH)" >> DEBIAN/control
echo Depends: libjansson4, libturbojpeg >> DEBIAN/control
echo Description: "${PROGRAM_NAME}" >> DEBIAN/control

cd ..
dpkg-deb --build "${PKG_ROOT}"

cd
rm -rf ${TMP}
