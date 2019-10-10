#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

mkdir ${TMP}
cd ${TMP}
git clone /tmp/ffmpeg.bundle
cd ffmpeg
#  --enable-libfaac --enable-gnutls
./configure --enable-gpl --enable-version3 --enable-nonfree --enable-libx264 --enable-libfreetype --enable-pic --enable-shared --enable-openssl
STATUS=$? ; if [ $STATUS != 0 ] ; then exit $STATUS ; fi

make -j4
STATUS=$? ; if [ $STATUS != 0 ] ; then exit $STATUS ; fi

make install
STATUS=$? ; if [ $STATUS != 0 ] ; then exit $STATUS ; fi

cd
rm -rf ${TMP}
exit $STATUS
