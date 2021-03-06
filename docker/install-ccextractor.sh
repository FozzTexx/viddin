#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}

git clone https://github.com/CCExtractor/ccextractor.git
cd ccextractor/linux
./build

cp ccextractor /usr/bin

cd
rm -rf ${TMP}
