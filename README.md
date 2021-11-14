This is a bunch of scripts I've put together to make it easy and largely automated to rip movies and TV series from DVD and Blu-Ray. Some of the main features are:

* Quickly rip all TV episodes from a disk
* Automatically put subtitles into a separate track
* Include both forced subtitles (if any) and complete subtitles in separate tracks
* Tools to search for TV intros and add Skip Intro and Skip Recap named chapters
* Include extra audio channels such as commentary in their own named tracks
* Split cartoon shorts into individual episodes out of their broadcast form (such as splitting Bugs Bunny or Woody Woodpecker cartoons into invidual shorts)

### Building and installing

Since these scripts rely on a lot of external programs such as HandBrake, FFmpeg, and makemkv that can be challenging to compile, I have made it easier by putting everything into a Docker container. To build, do:

    make -C docker

After the build completes, do:

    sudo cp docker/viddin-start /usr/local/bin/viddin

### The tools

Most of the tools are written in Python and have a --help option which will list the required arguments and the optional flags.

* rip-video: This is the main program which is able to transcode from one video format to another as well as rip videos directly from a DVD.
* rip-series: This makes it easy to rip all the episodes from a DVD. Once all episodes are ripped the disk is ejected.
* edit-chapters: Used to add, delete, and rename chapter markers.
* dvdorder: Will rename TV episodes to include titles.
* split-shorts: Uses episode information in a csv file to split TV episodes into their individual cartoon shorts.

Chris Osborn
<fozztexx@fozztexx.com>
http://insentricity.com
