#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -ex

echo "Finding current version"
MAKEMKV_URL="http://www.makemkv.com/download/"
MAKEMKV_CUR=$(wget --quiet -O - "${MAKEMKV_URL}" | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)

if [ -z "${MAKEMKV_CUR}" ]; then 
    echo "Unable to determine current makemkv version"
    exit 1
fi

mkdir ${TMP}
cd ${TMP}

echo "Downloading makemkv"
wget "${MAKEMKV_URL}makemkv-bin-${MAKEMKV_CUR}.tar.gz"
wget "${MAKEMKV_URL}makemkv-oss-${MAKEMKV_CUR}.tar.gz"

echo "Extracting makemkv"
tar xf makemkv-bin-${MAKEMKV_CUR}.tar.gz
tar xf makemkv-oss-${MAKEMKV_CUR}.tar.gz

PROGRAM_NAME=makemkv
VERSION="${MAKEMKV_CUR}"
PKG_ROOT="/tmp/${PROGRAM_NAME}"
mkdir -p "${PKG_ROOT}/usr"

echo "Building makemkv"
cd makemkv-oss-*/
./configure --prefix="${PKG_ROOT}/usr"
make
make install

cd ..

cd makemkv-bin-${MAKEMKV_CUR}
mkdir -p tmp
echo accepted > tmp/eula_accepted
make
make install PREFIX="${PKG_ROOT}/usr"

cd "${PKG_ROOT}"
mkdir DEBIAN
echo Package: "${PROGRAM_NAME}" >> DEBIAN/control
echo Version: "${VERSION}" >> DEBIAN/control
echo Maintainer: fozztexx@fozztexx.com >> DEBIAN/control
echo Architecture: "$(dpkg-architecture -q DEB_HOST_ARCH)" >> DEBIAN/control
echo Depends: libqt5widgets5 >> DEBIAN/control
echo Description: "${PROGRAM_NAME}" >> DEBIAN/control

cd ..
dpkg-deb --build "${PKG_ROOT}"

cd 
rm -rf ${TMP}
