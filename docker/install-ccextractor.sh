#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}

#git clone https://github.com/CCExtractor/ccextractor.git
git clone /tmp/ccextractor.bundle
cd ccextractor/linux
./build -without-rust

cp ccextractor /usr/bin

cd
rm -rf ${TMP}
