#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}
git clone /tmp/FFmpeg.bundle ffmpeg
cd ffmpeg
#  --enable-libfaac --enable-gnutls
./configure \
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

cd
rm -rf ${TMP}
