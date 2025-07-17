#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}

#git clone https://github.com/CCExtractor/ccextractor.git
git clone /tmp/ccextractor.bundle
cd ccextractor/linux
git checkout v0.94
./build -without-rust -disable_ocr

grep -E '^[A-Z][A-Z_]+=' ../package_creators/debian.sh  > /tmp/values
. /tmp/values

PKG_ROOT="/tmp/${PROGRAM_NAME}"
mkdir "${PKG_ROOT}"
cd "${PKG_ROOT}"

mkdir -p usr/bin
cp ${TMP}/ccextractor/linux/ccextractor usr/bin
make -C /tmp/gpac install DESTDIR=${PKG_ROOT}

mkdir DEBIAN
echo Package: "${PROGRAM_NAME}" >> DEBIAN/control
echo Version: "${VERSION}" >> DEBIAN/control
echo Maintainer: "${MAINTAINER}" >> DEBIAN/control
echo Architecture: "$(dpkg-architecture -q DEB_HOST_ARCH)" >> DEBIAN/control
echo Depends: libtesseract5, libglu1-mesa >> DEBIAN/control
echo Description: "${PROGRAM_NAME}" >> DEBIAN/control

cd ..
dpkg-deb --build "${PKG_ROOT}"

cd
rm -rf ${TMP}
