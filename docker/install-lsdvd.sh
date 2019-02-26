#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

mkdir ${TMP}
cd ${TMP}
git clone https://code.videolan.org/videolan/libdvdread.git
git clone https://git.code.sf.net/p/lsdvd/git lsdvd
cd libdvdread
autoreconf -i
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
./configure --prefix=/usr --disable-static
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
make
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
make install
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
cd ../lsdvd
autoreconf -i
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
./configure --prefix=/usr --disable-static
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
make
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
make install
STATUS=$?
if [ $STATUS -gt 0 ] ; then
    exit $STATUS
fi
cd ..
rm -rf ${TMP}
exit 0
