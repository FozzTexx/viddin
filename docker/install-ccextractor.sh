#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -x

mkdir ${TMP}
cd ${TMP}

git clone https://github.com/CCExtractor/ccextractor.git
cd ccextractor/linux
./build

cd
rm -rf ${TMP}
