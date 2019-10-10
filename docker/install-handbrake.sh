#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

mkdir ${TMP}
cd ${TMP}
#git clone https://github.com/HandBrake/HandBrake
git clone /tmp/HandBrake.bundle
STATUS=$? ; if [ $STATUS != 0 ] ; then exit $STATUS ; fi

cd HandBrake
#export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig/

echo Configuring
./configure --disable-gtk --launch && make --directory=build install
STATUS=$? ; if [ $STATUS != 0 ] ; then exit $STATUS ; fi

cd
rm -rf ${TMP}
exit $STATUS
