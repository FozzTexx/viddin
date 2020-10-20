#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e
VERSION=release-9.8.0

mkdir ${TMP}
cd ${TMP}

sudo apt install -y rake libboost-all-dev docbook-xsl xsltproc qt5-default

git clone -b ${VERSION} https://gitlab.com/mbunkus/mkvtoolnix.git

git submodule init
git submodule update
./configure
rake

cd
rm -rf ${TMP}
