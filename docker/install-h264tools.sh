#!/bin/sh
BASE=$(basename $0)
TMP=/tmp/${BASE}.$$

set -e

mkdir ${TMP}
cd ${TMP}
git clone /tmp/h264-tools.bundle 
cd h264-tools
patch -p1 <<EOF
diff --git a/ldecod/config_common.c b/ldecod/config_common.c
index 409ea53..ee1ffd7 100644
--- a/ldecod/config_common.c
+++ b/ldecod/config_common.c
@@ -61,6 +61,7 @@
 #include "configfile.h"
 #include "memalloc.h"
 
+InputParameters cfgparams;
 static int  ParameterNameToMapIndex (Mapping *Map, char *s);
 
 
diff --git a/ldecod/configfile.h b/ldecod/configfile.h
index 1e53e9a..326b104 100644
--- a/ldecod/configfile.h
+++ b/ldecod/configfile.h
@@ -18,7 +18,7 @@
 //#define LEVEL_IDC       21
 
 
-InputParameters cfgparams;
+extern InputParameters cfgparams;
 
 #ifdef INCLUDED_BY_CONFIGFILE_C
 // Mapping_Map Syntax:
diff --git a/ldecod/defines.h b/ldecod/defines.h
index 043f8c9..7cd45c5 100644
--- a/ldecod/defines.h
+++ b/ldecod/defines.h
@@ -236,7 +236,7 @@ enum {
   G_COMP = 4,    // G Component
   B_COMP = 5,    // B Component
   T_COMP = 6
-} ColorComponent;
+};
 
 enum {
   EOS = 1,    //!< End Of Sequence
EOF
mkdir build
cd build
cmake ..
make
make install

cd
rm -rf ${TMP}
