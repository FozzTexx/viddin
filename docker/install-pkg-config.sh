#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}

git clone git://anongit.freedesktop.org/pkg-config
STATUS=$? ; if [ $STATUS != 0 ] ; then exit $STATUS ; fi
cd pkg-config

sed -e 's/m4_copy/m4_copy_force/' -i glib/m4macros/glib-gettext.m4
autoreconf -i

./configure --prefix=/usr/local        \
	    --with-internal-glib       \
	    --disable-host-tool        \
	    --with-pc-path=/usr/lib/x86_64-linux-gnu/pkgconfig/ \
	    --docdir=/usr/share/doc/pkg-config-0.29.2

make -j4

make install

cd
rm -rf ${TMP}
