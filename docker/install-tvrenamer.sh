#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -x

mkdir ${TMP}
cd ${TMP}
git clone https://github.com/meermanr/TVSeriesRenamer
cp TVSeriesRenamer/tvrenamer.pl /usr/local/bin

cd
rm -rf ${TMP}
