# -*- mode: Fundamental; indent-tabs-mode: nil -*-

FROM ubuntu:20.04
LABEL maintainer fozztexx@fozztexx.com

ENV DEBIAN_FRONTEND noninteractive

ENV WSUSER viddin

RUN set -e \
    ; apt-get update \
    ; apt-get install -y \
	sudo \
	wget \
      	git \
        autoconf \
        bc \
        cmake \
        eject \
        libass-dev \
        libavcodec-dev \
        libavutil-dev \
        libbz2-dev \
        libdbd-mysql-perl \
        libdbi-perl \
        libdvdcss2 \
        libfreetype6-dev \
        libgd-gd2-perl \
        libglib2.0-dev \
        libjansson-dev \
        liblzma-dev \
        libmp3lame-dev \
        libnuma-dev \
        libopus-dev \
        libsamplerate-dev \
        libspeex-dev \
        libssl-dev \
        libterm-readkey-perl \
        libtesseract-dev \
        libtheora-dev \
        libtool-bin \
        libturbojpeg0-dev \
        libvorbis-dev \
        libvpx-dev \
        libwww-perl \
        libx264-dev \
        libxml2-dev \
        lsdvd \
        m4 \
        mediainfo \
        meson \
        mkvtoolnix \
        mplayer \
        nasm \
        python \
        python3 \
        python3-pip \
        qt5-default \
        setcd \
        sox \
        tesseract-ocr \
    ; rm -rf /var/lib/apt/lists/* \
      \
    ; pip3 install \
        requests-cache==0.5.2 \
        termcolor \
        tvdb_api==2.0 \
        xmltodict \
    ; setsid sh -c "yes | dpkg-reconfigure libdvd-pkg" \
      \
    ; useradd -s /bin/bash $WSUSER \
    ; eval WSHOME=~$WSUSER \
    ; mkdir $WSHOME \
    ; chown $WSUSER.$WSUSER $WSHOME \
    ; usermod -aG cdrom $WSUSER \
    ; echo "$WSUSER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    ;

# Install pkg-config from source
COPY install-pkg-config.sh /tmp/
RUN /tmp/install-pkg-config.sh && rm /tmp/install-pkg-config.sh

# Install HandBrake
COPY install-handbrake.sh HandBrake.bundle /tmp/
RUN /tmp/install-handbrake.sh && rm /tmp/install-handbrake.sh && rm /tmp/HandBrake.bundle

# Install ffmpeg
COPY install-ffmpeg.sh ffmpeg.bundle /tmp/
RUN /tmp/install-ffmpeg.sh && rm /tmp/install-ffmpeg.sh && rm /tmp/ffmpeg.bundle

# Install makemkv
COPY install-ccextractor.sh /tmp/
RUN /tmp/install-ccextractor.sh && rm /tmp/install-ccextractor.sh
COPY install-makemkv.sh /tmp/
RUN /tmp/install-makemkv.sh && rm /tmp/install-makemkv.sh

COPY install-tvrenamer.sh /tmp/
RUN /tmp/install-tvrenamer.sh && rm /tmp/install-tvrenamer.sh

# Copy init script
COPY viddin-init /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/viddin-init"]

# Install viddin scripts
ADD viddin.tar /usr/local/bin
