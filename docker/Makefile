IMAGE=viddin
VERSION=1.0
BUNDLES=HandBrake.bundle ffmpeg.bundle viddin.tar
SCRIPTS=adjust-volume convert2dv copy-tape dvdls dvdorder edit-chapters find-black \
	find-silence guess-chapters restore-ntsc rip-series rip-video split-garfield \
	split-video subinfo trackinfo trim-shorts vidinf
OSCRIPTS=$(addprefix ../,$(SCRIPTS))

docker-build: Dockerfile viddin-init install-handbrake.sh $(BUNDLES)
	docker build -f Dockerfile --rm -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

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
