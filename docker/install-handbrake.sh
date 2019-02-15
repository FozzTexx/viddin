#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

mkdir ${TMP}
cd ${TMP}
#git clone https://github.com/HandBrake/HandBrake
git clone /tmp/HandBrake.bundle
cd HandBrake
echo Configuring
./configure --disable-gtk --launch && make --directory=build install
STATUS=$?
cd ..
rm -rf ${TMP}
exit $STATUS
