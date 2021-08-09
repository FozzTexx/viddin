IMAGE=viddin
VERSION=1.0
BUNDLES=HandBrake.bundle ffmpeg.bundle viddin.tar
SCRIPTS=$(shell git ls-tree --full-tree -r --name-only --full-name HEAD | sed -e '/^docker/d')
OSCRIPTS=$(addprefix ../,$(SCRIPTS))

docker-build: Dockerfile viddin-init install-handbrake.sh $(BUNDLES)
	docker build $(REBUILDFLAGS) -f Dockerfile \
	  --rm -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

# To force a complete clean build, do:
#   make rebuild
rebuild:
	make REBUILDFLAGS="--no-cache --pull"

HandBrake.bundle:
	git clone --mirror https://github.com/HandBrake/HandBrake
	git --git-dir HandBrake.git bundle create $@ --all
	rm -rf HandBrake.git

ffmpeg.bundle:
	git clone --mirror https://github.com/FozzTexx/FFmpeg.git
	git --git-dir FFmpeg.git bundle create $@ --all
	rm -rf FFmpeg.git

viddin.tar: $(OSCRIPTS)
	tar -cf $@ -C .. $(SCRIPTS)
