FROM ubuntu:20.04
LABEL maintainer fozztexx@fozztexx.com

ENV DEBIAN_FRONTEND noninteractive

# Install useful things
RUN apt-get update && apt-get install -y git wget sudo python3 python3-pip python

# Install build tools
RUN apt-get update && apt-get install -y m4 autoconf cmake libtool-bin nasm

# Install pkg-config from source
#RUN apt-get update && apt-get install -y libglib2.0-dev
COPY install-pkg-config.sh /tmp/
RUN /tmp/install-pkg-config.sh && rm /tmp/install-pkg-config.sh

# Install HandBrake
RUN apt-get update && apt-get install -y libmp3lame-dev libopus-dev libspeex-dev libvpx-dev \
    libxml2-dev libjansson-dev libx264-dev libass-dev libvorbis-dev libsamplerate-dev \
    libtheora-dev libbz2-dev liblzma-dev meson libnuma-dev libturbojpeg0-dev
COPY install-handbrake.sh HandBrake.bundle /tmp/
RUN /tmp/install-handbrake.sh && rm /tmp/install-handbrake.sh && rm /tmp/HandBrake.bundle

# Install ffmpeg
RUN apt-get update && apt-get install -y libfreetype6-dev libssl-dev
COPY install-ffmpeg.sh ffmpeg.bundle /tmp/
RUN /tmp/install-ffmpeg.sh && rm /tmp/install-ffmpeg.sh && rm /tmp/ffmpeg.bundle

# Install makemkv
RUN apt-get update && apt-get install -y qt5-default tesseract-ocr libtesseract-dev libavcodec-dev libavutil-dev
COPY install-ccextractor.sh /tmp/
RUN /tmp/install-ccextractor.sh && rm /tmp/install-ccextractor.sh
COPY install-makemkv.sh /tmp/
RUN /tmp/install-makemkv.sh && rm /tmp/install-makemkv.sh

# Install tools viddin scripts need
RUN apt-get update && apt-get install -y libdvdcss2 mkvtoolnix eject mediainfo mplayer bc sox
RUN setsid sh -c "yes | dpkg-reconfigure libdvd-pkg"
RUN pip3 install xmltodict termcolor tvdb_api==2.0

RUN apt-get update && apt-get install -y lsdvd setcd
# # Install lsdvd from source because stock one is broken
# COPY install-lsdvd.sh /tmp/
# RUN /tmp/install-lsdvd.sh && rm /tmp/install-lsdvd.sh

RUN apt-get update && apt-get install -y libterm-readkey-perl libwww-perl libdbi-perl libdbd-mysql-perl libgd-gd2-perl
COPY install-tvrenamer.sh /tmp/
RUN /tmp/install-tvrenamer.sh && rm /tmp/install-tvrenamer.sh

# Setup user
ENV WSUSER viddin
RUN useradd -s /bin/bash $WSUSER && eval WSHOME=~$WSUSER && mkdir $WSHOME && chown $WSUSER.$WSUSER $WSHOME && usermod -aG cdrom $WSUSER
RUN echo "$WSUSER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Copy init script
COPY viddin-init /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/viddin-init"]

# Install viddin scripts
ADD viddin.tar /usr/local/bin
