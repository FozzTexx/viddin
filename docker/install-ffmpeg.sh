#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -x

mkdir ${TMP}
cd ${TMP}
git clone /tmp/ffmpeg.bundle
cd ffmpeg
#  --enable-libfaac --enable-gnutls
./configure --enable-gpl --enable-version3 --enable-nonfree --enable-libx264 --enable-libfreetype --enable-pic --enable-shared --enable-openssl

make -j4
make install

cd
rm -rf ${TMP}
