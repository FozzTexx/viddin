# -*- mode: Fundamental; indent-tabs-mode: nil -*-

ARG BASE=ubuntu:22.04

# Build CCExtractor
FROM ${BASE} as ccextractor
RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        clang \
        cmake \
        dpkg-dev \
        gcc \
        git \
        libclang-dev \
        libcurl4-gnutls-dev \
        libglew-dev \
        libglfw3-dev \
        libgpac-dev \
        libleptonica-dev \
        libtesseract-dev \
        tesseract-ocr \
    ; rm -rf /var/lib/apt/lists/* \
    ;

COPY install-ccextractor.sh ccextractor.bundle /tmp/
RUN set -e \
    ; /tmp/install-ccextractor.sh \
    ; rm /tmp/install-ccextractor.sh /tmp/ccextractor.bundle \
    ;

# Build OCR models
FROM ${BASE} as omz-ocr
RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        python3-pip \
    ; rm -rf /var/lib/apt/lists/* \
      \
    ; pip3 install \
        onnx \
        openvino-dev \
        torch \
        torchvision \
    ;

RUN set -e \
    ; omz_downloader \
                     --name horizontal-text-detection-0001,text-recognition-resnet-fc \
                     --output_dir /home/viddin/open_model_zoo_models \
                     --cache_dir /home/viddin/open_model_zoo_cache \
                     --precision FP32 \
    ; omz_converter \
                    --name text-recognition-resnet-fc \
                    --precisions FP32 \
                    --download_dir /home/viddin/open_model_zoo_models \
                    --output_dir /home/viddin/open_model_zoo_models \
    ;

# Build HandBrake
FROM ${BASE} as handbrake
RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        autoconf \
        automake \
        binutils \
        build-essential \
        ca-certificates \
        cmake \
        gcc \
        git \
        libass-dev \
        libbz2-dev \
        libfontconfig-dev \
        libfreetype-dev \
        libfribidi-dev \
        libharfbuzz-dev \
        libjansson-dev \
        liblzma-dev \
        libmp3lame-dev \
        libnuma-dev \
        libogg-dev \
        libopus-dev \
        libsamplerate0-dev \
        libspeex-dev \
        libtheora-dev \
        libtool \
        libtool-bin \
        libturbojpeg0-dev \
        libvorbis-dev \
        libvpx-dev \
        libx264-dev \
        libxml2-dev \
        m4 \
        make \
        meson \
        nasm \
        ninja-build \
        patch \
        pkg-config \
        python3 \
        tar \
        zlib1g-dev \
    ; rm -rf /var/lib/apt/lists/* \
    ;

COPY install-handbrake.sh HandBrake.bundle /tmp/
RUN set -e \
    ; /tmp/install-handbrake.sh \
    ; rm /tmp/install-handbrake.sh /tmp/HandBrake.bundle \
    ;

# Build ffmpeg
FROM ${BASE} as ffmpeg
RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        build-essential \
        git \
        libass-dev \
        libfreetype6-dev \
        libmp3lame-dev \
        libssl-dev \
        libx264-dev \
        libx265-dev \
        nasm \
    ; rm -rf /var/lib/apt/lists/* \
    ;

COPY install-ffmpeg.sh FFmpeg.bundle /tmp/
RUN set -e \
    ; /tmp/install-ffmpeg.sh \
    ; rm /tmp/install-ffmpeg.sh /tmp/FFmpeg.bundle \
    ;

# Build makemkv
FROM ${BASE} as makemkv
RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        file \
        libavcodec-dev \
        libc6-dev \
        libexpat1-dev \
        libgl1-mesa-dev \
        libssl-dev \
        pkg-config \
        qtbase5-dev \
        wget \
        zlib1g-dev \
    ; rm -rf /var/lib/apt/lists/* \
    ;

COPY --from=ccextractor /tmp/ccextractor.deb /tmp/
RUN set -e \
    ; apt-get update \
    ; apt-get install -y /tmp/ccextractor.deb \
    ; rm -rf /var/lib/apt/lists/* /tmp/ccextractor.deb \
    ;

COPY install-makemkv.sh /tmp/
RUN set -e \
    ; /tmp/install-makemkv.sh \
    ; rm /tmp/install-makemkv.sh \
    ;

# Build h264-tools
FROM ${BASE} as h264-tools
RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        cmake \
        g++ \
        git \
        make \
        patch \
    ; rm -rf /var/lib/apt/lists/* \
    ;

COPY install-h264tools.sh h264-tools.bundle /tmp/
RUN set -e \
    ; /tmp/install-h264tools.sh \
    ; rm /tmp/install-h264tools.sh /tmp/h264-tools.bundle \
    ;

# Assemble all the pieces together for final image
FROM ${BASE}
LABEL maintainer fozztexx@fozztexx.com

ENV DEBIAN_FRONTEND noninteractive
ENV WSUSER viddin

RUN set -e \
    ; apt-get update \
    ; apt-get install -y --no-install-recommends \
        eject \
        git \
        libdvd-pkg \
        lsdvd \
        mediainfo \
        mkvtoolnix \
        mplayer \
        python3-pillow \
        python3-pip \
        python3-pytimeparse \
        setcd \
        sox \
        sudo \
    ; rm -rf /var/lib/apt/lists/* \
      \
    ; pip3 install \
        tesserocr \
    ; pip3 install \
        librosa \
        opencv-python \
        openvino \
        requests-cache==0.5.2 \
        termcolor \
        tvdb_api==2.0 \
        xmltodict \
    ;

RUN set -e \
    ; setsid sh -c "yes | dpkg-reconfigure libdvd-pkg" \
      \
    ; useradd -s /bin/bash $WSUSER \
    ; eval WSHOME=~$WSUSER \
    ; mkdir -p $WSHOME \
    ; chown -R $WSUSER.$WSUSER $WSHOME \
    ; usermod -aG cdrom $WSUSER \
    ; echo "$WSUSER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    ;

COPY install-tvrenamer.sh /tmp/
RUN /tmp/install-tvrenamer.sh && rm /tmp/install-tvrenamer.sh

RUN mkdir -p /tmp/packages
COPY --from=ccextractor /tmp/ccextractor.deb /tmp/packages/
COPY --from=handbrake /tmp/handbrake.deb /tmp/packages/
COPY --from=ffmpeg /tmp/ffmpeg.deb /tmp/packages/
COPY --from=makemkv /tmp/makemkv.deb /tmp/packages/
RUN set -e \
    ; apt-get update \
    ; apt-get install -y /tmp/packages/*.deb \
    ; rm -rf /var/lib/apt/lists/* /tmp/packages \
    ;

COPY --from=omz-ocr /home/viddin/open_model_zoo_models /home/viddin/open_model_zoo_models
COPY --from=h264-tools \
       /usr/local/bin/mkv2mkv \
       /usr/local/bin/ldecod \
       /usr/local/bin/naluparser \
       /usr/local/bin/yuvsbspipe \
      /usr/local/bin/

# Copy init script
COPY viddin-init /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/viddin-init"]

# Install viddin scripts
ADD viddin.tar /usr/local/bin
