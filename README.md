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
* dvdls: List the titles on a DVD.

### Examples

To rip from a single title that was originally film (24 fps) and was telecined (29.97 fps interlaced) on a DVD and convert to progressive:

    rip-video --film --title 4 output.mkv

To rip from an NTSC (29.97 fps interlaced) to progressive:

    rip-video --tv --title 4 output.mkv

To rip all the episodes from a single disk:

    dvdls
    rip-series 3 7 2 3 4 5

Use `dvdls` to get the list of titles on the disk and determine which ones are the actual TV episodes, in this example the titles would be 2 3 4 5. Then use `rip-series` by specifying the season number (3 in the above example) and first episode number (7 in the above example) followed by the list of titles on the DVD. When the rip completes without errors it will eject the disk and you can insert the next one, do the `dvdls` again and then `rip-series` again but updating the episode number, which would be 11 since 7 + 4 titles = 11.
    
Chris Osborn
<fozztexx@fozztexx.com>
http://insentricity.com
