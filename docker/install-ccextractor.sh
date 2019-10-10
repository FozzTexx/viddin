#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

mkdir ${TMP}
cd ${TMP}

git clone https://github.com/CCExtractor/ccextractor.git
cd ccextractor/linux
./build
STATUS=$?
if [ $STATUS = 0 ] ; then
    cp ccextractor /usr/bin
fi

cd
rm -rf ${TMP}
exit $STATUS
