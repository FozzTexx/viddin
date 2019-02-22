FROM ubuntu:18.04
LABEL maintainer fozztexx@fozztexx.com

#Install useful things
RUN apt-get update && apt-get install -y git wget sudo python3 python3-pip python

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
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y lsdvd libdvdcss2 mkvtoolnix eject mediainfo mplayer bc
RUN setsid sh -c "yes | dpkg-reconfigure libdvd-pkg"
RUN pip3 install xmltodict termcolor tvdb_api
ADD viddin.tar /usr/local/bin

# Setup user
ENV WSUSER viddin
RUN useradd -s /bin/bash $WSUSER && eval WSHOME=~$WSUSER && mkdir $WSHOME && chown $WSUSER.$WSUSER $WSHOME && usermod -aG cdrom $WSUSER
RUN echo "$WSUSER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Copy init script
COPY viddin-init /usr/local/bin/
