IMAGE=viddin
VERSION=1.0

docker-build: Dockerfile viddin-init install-handbrake.sh HandBrake.bundle ffmpeg.bundle
	docker build --rm -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

HandBrake.bundle:
	git clone --mirror https://github.com/HandBrake/HandBrake
	git --git-dir HandBrake.git bundle create $@ --all
	rm -rf HandBrake.git

ffmpeg.bundle:
	git clone --mirror https://github.com/FozzTexx/FFmpeg.git
	git --git-dir FFmpeg.git bundle create $@ --all
	rm -rf FFmpeg.git
