IMAGE=viddin
VERSION=2.0
BUNDLES=HandBrake.bundle FFmpeg.bundle ccextractor.bundle h264-tools.bundle viddin.tar
SCRIPTS=$(shell git ls-tree --full-tree -r --name-only --full-name HEAD | sed -e '/^docker/d')
OSCRIPTS=$(addprefix ../,$(SCRIPTS))

docker-build: Dockerfile viddin-init install-handbrake.sh $(BUNDLES)
	env BUILDKIT_PROGRESS=plain \
	  docker build $(REBUILDFLAGS) -f Dockerfile \
	    --rm -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

# To force a complete clean build, do:
#   make rebuild
rebuild:
	rm -f $(BUNDLES)
	make REBUILDFLAGS="--no-cache --pull"

HandBrake.bundle:
	URL=https://github.com/HandBrake && PKG=$(basename $@) && CURDIR=$${PWD} && TMP=/tmp/viddin.$$$$ && mkdir $${TMP} && cd $${TMP} && git -c http.sslVerify=false clone $${URL}/$${PKG}.git && cd $${PKG} && git bundle create ../$${PKG}.bundle --all && cd $${CURDIR} && mv $${TMP}/$${PKG}.bundle . && rm -rf $${TMP}

FFmpeg.bundle:
	URL=https://github.com/FozzTexx && PKG=$(basename $@) && CURDIR=$${PWD} && TMP=/tmp/viddin.$$$$ && mkdir $${TMP} && cd $${TMP} && git -c http.sslVerify=false clone $${URL}/$${PKG}.git && cd $${PKG} && git bundle create ../$${PKG}.bundle --all && cd $${CURDIR} && mv $${TMP}/$${PKG}.bundle . && rm -rf $${TMP}

ccextractor.bundle:
	URL=https://github.com/CCExtractor && PKG=$(basename $@) && CURDIR=$${PWD} && TMP=/tmp/viddin.$$$$ && mkdir $${TMP} && cd $${TMP} && git -c http.sslVerify=false clone $${URL}/$${PKG}.git && cd $${PKG} && git bundle create ../$${PKG}.bundle --all && cd $${CURDIR} && mv $${TMP}/$${PKG}.bundle . && rm -rf $${TMP}

h264-tools.bundle:
	URL=https://github.com/carrardt && PKG=$(basename $@) && CURDIR=$${PWD} && TMP=/tmp/viddin.$$$$ && mkdir $${TMP} && cd $${TMP} && git -c http.sslVerify=false clone $${URL}/$${PKG}.git && cd $${PKG} && git bundle create ../$${PKG}.bundle --all && cd $${CURDIR} && mv $${TMP}/$${PKG}.bundle . && rm -rf $${TMP}

viddin.tar: $(OSCRIPTS)
	tar -cf $@ -C .. $(SCRIPTS)
