FROM ubuntu:18.04
LABEL maintainer fozztexx@fozztexx.com

#Install useful things
RUN apt-get update && apt-get install -y git wget sudo python3 python3-pip python

ENV WSUSER viddin
RUN useradd -s /bin/bash $WSUSER && eval WSHOME=~$WSUSER && mkdir $WSHOME && chown $WSUSER.$WSUSER $WSHOME
RUN echo "$WSUSER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

COPY viddin-init /usr/local/bin/

# Install build tools
RUN apt-get update && apt-get install -y m4 autoconf cmake libtool-bin pkg-config nasm

# Install HandBrake
RUN apt-get update && apt-get install -y libmp3lame-dev libopus-dev libspeex-dev libvpx-dev \
    libxml2-dev libjansson-dev libx264-dev libass-dev libvorbis-dev libsamplerate-dev \
    libtheora-dev libbz2-dev liblzma-dev
COPY install-handbrake.sh HandBrake.bundle /tmp/
RUN /tmp/install-handbrake.sh && rm /tmp/install-handbrake.sh && rm /tmp/HandBrake.bundle

# Install ffmpeg
RUN apt-get update && apt-get install -y libfreetype6-dev libssl-dev
COPY install-ffmpeg.sh ffmpeg.bundle /tmp/
RUN /tmp/install-ffmpeg.sh && rm /tmp/install-ffmpeg.sh && rm /tmp/ffmpeg.bundle

# Install viddin scripts
RUN pip3 install xmltodict termcolor
RUN apt-get update && apt-get install -y mkvtoolnix
ADD viddin.tar /usr/local/bin
