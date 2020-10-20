#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}
git clone https://code.videolan.org/videolan/libdvdread.git
git clone https://git.code.sf.net/p/lsdvd/git lsdvd
cd libdvdread
autoreconf -i
./configure --prefix=/usr --disable-static
make
make install

cd ../lsdvd
autoreconf -i
./configure --prefix=/usr --disable-static
make
make install

cd
rm -rf ${TMP}
