#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

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

echo "Building makemkv"
cd makemkv-oss-${MAKEMKV_CUR}
./configure && make && make install
STATUS=$?
cd ..

if [ $STATUS = 0 ] ; then
    cd makemkv-bin-${MAKEMKV_CUR}
    mkdir -p tmp
    echo accepted > tmp/eula_accepted
    make && make install
    STATUS=$?
    cd ..
fi

rm -rf ${TMP}
exit $STATUS
