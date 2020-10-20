#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}
git clone https://github.com/meermanr/TVSeriesRenamer
cp TVSeriesRenamer/tvrenamer.pl /usr/local/bin

cd
rm -rf ${TMP}
