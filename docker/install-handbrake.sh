#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -x

mkdir ${TMP}
cd ${TMP}
#git clone https://github.com/HandBrake/HandBrake
git clone /tmp/HandBrake.bundle

cd HandBrake
#export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig/

echo Configuring
./configure --disable-gtk --launch && make --directory=build install

cd
rm -rf ${TMP}
