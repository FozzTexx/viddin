# Copyright 2019 by Chris Osborn <fozztexx@fozztexx.com>
#
# This file is part of viddin.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License at <http://www.gnu.org/licenses/> for
# more details.

import os
import pty
import subprocess
import json
import xmltodict
import re
import datetime
import sys

# This class is mostly just used to put all the functions in their own namespace
class viddin:
  @staticmethod
  def decodeTimecode(tc):
    fraction = 0
    if re.match(".*[.,][0-9]+$", tc):
      parts = re.split("[.,]", tc)
      fraction = float("."+parts[1])
      tc = parts[0]

    seconds = sum(int(x) * 60 ** i for i,x in enumerate(reversed(tc.split(":"))))
    seconds += fraction
    return seconds

  @staticmethod
  def formatTimecode(tc):
    ft = str(datetime.timedelta(seconds = tc))
    p = re.compile(r'^[0:]+')
    m = p.search(ft)
    if m:
      ft = ft[m.span()[1]:]
    dp = ft.rfind(".")
    if dp >= 0 and dp < len(ft) - 4:
      ft = ft[:dp+4]
    return ft

  @staticmethod
  def formatChapter(seconds):
    hours = int(seconds / 3600)
    minutes = int((seconds / 60) % 60)
    return "%02i:%02i:%06.3f" % (hours, minutes, seconds - hours * 3600 - minutes * 60)

  @staticmethod
  def loadChapters(filename):
    chapters = []
    with os.popen("ffmpeg -i \"" + filename + "\" -f ffmetadata 2>&1 | grep 'Chapter #'") as f:
      for line in f:
        fields = line.split()
        begin = float(re.sub(",", "", fields[3]))
        chapters.append(begin)
    return chapters

  @staticmethod
  def loadChapterFile(filename):
    chapters = []
    with open(filename) as f:
      for line in f:
        fields = line.split("\t")
        begin = viddin.decodeTimecode(fields[1])
        chapters.append(begin)
    return chapters

  @staticmethod
  def subWithUid(uid, subs):
    for track in subs:
      if 'uid' in track and uid == track['uid']:
        return track
    return None

  # FIXME - call get tracks and filter out the subs
  @staticmethod
  def getSubs(path, title=None, debugFlag=False):
    subs = []
    _, ext = os.path.splitext(path)
    if title is not None:
      cmd = "lsdvd -t %i -s \"%s\"" % (int(title), path)
      if debugFlag:
        print(cmd)
      else:
        cmd += " 2>/dev/null"
      with os.popen(cmd) as f:
        for line in f:
          fields = line.split()
          if len(fields) and fields[0] == "Subtitle:":
            key = None
            val = None
            end = False
            values = {}
            for field in fields[2:]:
              if field[-1] == ':':
                key = field[:-1]
              else:
                if field[-1] == ',':
                  end = True
                  field = field[:-1]
                if not val:
                  val = field
                else:
                  if not isinstance(val, list):
                    val = [val]
                  val.append(field)
              if end:
                values[key] = val
                end = False
                key = None
                val = None
            subs.append(values)
    elif ext == ".mkv":
      cmd = "mkvmerge -i -F json \"%s\"" % (path)
      if debugFlag:
        print(cmd)
      process = os.popen(cmd)
      jstr = process.read()
      process.close()
      jinfo = json.loads(jstr)

      for track in jinfo['tracks']:
        if track['type'] == "subtitles":
          info = {}
          info['rv_track_id'] = track['id'] 
          info.update(track['properties'])
          subs.append(info)

      cmd = "mkvextract tags \"%s\"" % (path)
      if debugFlag:
        print(cmd)
      process = os.popen(cmd)
      xstr = process.read()
      process.close()
      xstr = xstr.strip()
      if len(xstr):
        xinfo = xmltodict.parse(xstr)['Tags']
        xlist = []
        for track in xinfo:
          xi1 = xinfo[track]
          for xi2 in xi1:
            xdict = {}
            if 'Targets' in xi2:
              xi3 = xi2['Targets']
              if xi3 and 'TrackUID' in xi3:
                xdict['TrackUID'] = int(xi3['TrackUID'])
            if 'Simple' in xi2:
              xi3 = xi2['Simple']
              if isinstance(xi3, list):
                for xi4 in xi3:
                  xdict[xi4['Name']] = xi4['String']
              else:
                xdict[xi3['Name']] = xi3['String']
            xlist.append(xdict)

        for track in xlist:
          if 'TrackUID' in track:
            sub = viddin.subWithUid(track['TrackUID'], subs)
            if sub:
              sub.update(track)

    return subs

  @staticmethod
  def findLength(info):
    idx = info.index("Length:")
    str = info[idx+1]
    if str[-1] == ',':
      str = str[:-2]
    return viddin.decodeTimecode(str)

  @staticmethod
  def trackWithUid(uid, tracks):
    for track in tracks:
      if 'uid' in track and uid == track['uid']:
        return track
    return None

  @staticmethod
  def getLengthMKV(path, debugFlag=False):
    cmd = "mkvmerge -i -F json \"%s\"" % (path)
    if debugFlag:
      print(cmd)
    process = os.popen(cmd)
    jstr = process.read()
    process.close()
    jinfo = json.loads(jstr)

    tracks = []
    for track in jinfo['tracks']:
      info = {'type': track['type']}
      info['rv_track_id'] = track['id']
      info.update(track['properties'])
      tracks.append(info)

    cmd = "mkvextract tags \"%s\"" % (path)
    if debugFlag:
      print(cmd)
    process = os.popen(cmd)
    xstr = process.read()
    process.close()
    xstr = xstr.strip()
    if len(xstr):
      xinfo = xmltodict.parse(xstr)['Tags']
      xlist = []
      for track in xinfo:
        xi1 = xinfo[track]
        for xi2 in xi1:
          xdict = {}
          if 'Targets' in xi2:
            xi3 = xi2['Targets']
            if xi3 and 'TrackUID' in xi3:
              xdict['TrackUID'] = int(xi3['TrackUID'])
          if 'Simple' in xi2:
            xi3 = xi2['Simple']
            if type(xi3) == list:
              for xi4 in xi3:
                xdict[xi4['Name']] = xi4['String']
            else:
              xdict[xi3['Name']] = xi3['String']
          xlist.append(xdict)

      for track in xlist:
        if 'TrackUID' in track:
          tt = viddin.trackWithUid(track['TrackUID'], tracks)
          if tt:
            tt.update(track)

    tlen = None
    for track in tracks:
      if track['type'] == "video" and 'DURATION' in track:
        alen = viddin.decodeTimecode(track['DURATION'])
        if not tlen or alen > tlen:
          tlen = alen

    if not tlen:
      container = jinfo['container']['properties']
      if 'duration' in container:
        tlen = int(container['duration'])
        tlen /= 1000000000
    return tlen

  @staticmethod
  def getLength(filename, title=None, chapters=None, debugFlag=False):
    clen = []
    if title:
      cmd = "lsdvd -t %s -c \"%s\"" % (title, filename)
      if debugFlag:
        print(cmd)
      else:
        cmd += " 2>/dev/null"
      with os.popen(cmd) as f:
        lines = f.read().splitlines()
      for line in lines:
        info = line.split()
        if len(info) < 1:
          continue
        if info[0] == "Title:":
          tlen = viddin.findLength(info)
        elif info[0] == "Chapter:":
          clen.append(viddin.findLength(info))
      if chapters:
        if chapters.index("-"):
          chaps = chapters.split("-")
        else:
          chaps = [chapters, chapters]
        tlen = 0
        for c in range(int(chaps[0]), int(chaps[1]) + 1):
          tlen += clen[c]
    else:
      _, ext = os.path.splitext(filename)
      if ext == ".mkv":
        tlen = viddin.getLengthMKV(filename)
      else:
        cmd = "vidinf \"%s\" | grep ID_LENGTH | sed -e 's/ID_LENGTH=//'" % filename
        if debugFlag:
          print(cmd)
        process = os.popen(cmd)
        tlen = float(process.read())
        process.close()

      if chapters:
        if chapters.index("-"):
          chaps = chapters.split("-")
        else:
          chaps = [chapters, chapters]
        chaptimes = viddin.loadChapters(filename)
        chaptimes.append(tlen)
        tlen = abs(chaptimes[int(chaps[1])] - chaptimes[int(chaps[0]) - 1])
        if debugFlag:
          print("Chapters", chaptimes[int(chaps[0]) - 1], chaptimes[int(chaps[1])])

    return tlen

  @staticmethod
  def runCommand(cmd):
    width = os.get_terminal_size().columns
    pos = 0
    master, slave = pty.openpty()
    with subprocess.Popen(cmd, shell=True, stdin=slave, stdout=slave, stderr=slave,
                         close_fds=True) as p:
      m = os.fdopen(master, 'r')
      os.close(slave)
      try:
        while True:
          c = m.read(1)
          if c == '\n':
            c = '\r'
          if c == '\r' or width == 0 or pos < width - 2:
            sys.stdout.write(c)
            pos += 1
            if c == '\r':
              pos = 0
          sys.stdout.flush()
      except OSError:
        pass
    return

  @staticmethod
  def findBlack(filename):
    video, ext = os.path.splitext(filename)
    if not os.path.exists("%s.blk" % video):
      print("Finding black")
      cmd = "find-black --duration 0.05 \"%s\" \"%s.blk\" > /dev/null" \
            % (filename.replace("\"", "\\\""), video.replace("\"", "\\\""))
      os.system(cmd)

  @staticmethod
  def findSilence(filename):
    video, ext = os.path.splitext(filename)
    if not os.path.exists("%s.sil" % video):
      print("Finding silence")
      cmd = "find-silence --threshold 40 --duration 0.01 \"%s\" \"%s.sil\" > /dev/null" \
            % (filename.replace("\"", "\\\""), video.replace("\"", "\\\""))
      os.system(cmd)

  @staticmethod
  def loadSplits(filename):
    splits = []
    with open(filename) as f:
      for line in f:
        info = line.split()
        begin = float(info[1])
        end = float(info[2])
        center = begin + (end - begin) / 2
        splits.append([center, begin, end])
    return splits

  @staticmethod
  def bestSilence(best):
    global silence

    bestsil = None
    for info in silence:
      begin = float(info[1])
      end = float(info[2])
      center = begin + (end - begin) / 2
      diff = abs(center - best[0])
      if ((begin >= best[1] and begin <= best[2]) or (end >= best[1] and end <= best[2]) or \
            (best[1] >= begin and best[1] <= end) or (best[2] >= begin and best[2] <= end)) \
            and (not bestsil or diff < bestsil[0]):
        bestsil = [diff, center, begin, end]

    if bestsil:
      begin = bestsil[2]
      if begin < best[1]:
        begin = best[1]
      end = bestsil[3]
      if end > best[2]:
        end = best[2]
      return [begin, end]

    return None

  @staticmethod
  def getTracks(path, title=None):
    tracks = []
    if title != None:
      cmd = "lsdvd -t %i -s %s" % (int(title), path)
      with os.popen(cmd) as f:
        for line in f:
          fields = line.split()
          if len(fields):
            key = None
            val = None
            end = False
            values = {}
            for field in fields[2:]:
              if field[-1] == ':':
                key = field[:-1]
              else:
                if field[-1] == ',':
                  end = True
                  field = field[:-1]
                if not val:
                  val = field
                else:
                  if not isinstance(val, list):
                    val = [val]
                  val.append(field)
              if end:
                values[key] = val
                end = False
                key = None
                val = None
            tracks.append(values)
    else:
      cmd = "mkvmerge -i -F json \"%s\"" % (path)
      process = os.popen(cmd)
      jstr = process.read()
      process.close()
      jinfo = json.loads(jstr)

      for track in jinfo['tracks']:
        info = {'type': track['type']}
        info['rv_track_id'] = track['id']
        info.update(track['properties'])
        tracks.append(info)

      cmd = "mkvextract tags \"%s\"" % (path)
      process = os.popen(cmd)
      xstr = process.read()
      process.close()
      xstr = xstr.strip()
      if len(xstr):
        xinfo = xmltodict.parse(xstr)['Tags']
        xlist = []
        for track in xinfo:
          xi1 = xinfo[track]
          for xi2 in xi1:
            xdict = {}
            if 'Targets' in xi2:
              xi3 = xi2['Targets']
              if xi3 and 'TrackUID' in xi3:
                xdict['TrackUID'] = int(xi3['TrackUID'])
            if 'Simple' in xi2:
              xi3 = xi2['Simple']
              if type(xi3) == list:
                for xi4 in xi3:
                  xdict[xi4['Name']] = xi4['String']
              else:
                xdict[xi3['Name']] = xi3['String']
            xlist.append(xdict)

        for track in xlist:
          if 'TrackUID' in track:
            tt = trackWithUid(track['TrackUID'], tracks)
            if tt:
              tt.update(track)

    return tracks

  @staticmethod
  def loadEpisodeInfoCSV(filename):
    series = []
    f = open(filename, 'rU')
    try:
      reader = csv.reader(f)
      for row in reader:
        epnum = re.split(" *x *", row[CSV_EPISODE])
        dvdep = row[CSV_DVDEP]
        if not re.match(".*x.*", dvdep):
          dvdep = row[CSV_EPISODE] + "." + dvdep
        dvdnum = re.split(" *x *", dvdep)
        epid = epnum[0] + "x" + epnum[1].zfill(2)
        info = [int(epnum[0]), int(epnum[1]), int(dvdnum[0]), float(dvdnum[1]),
                row[CSV_TITLE], row[CSV_ORIGDATE]]
        series.append(info)
    finally:
      f.close()
    return series

  @staticmethod
  def loadEpisodeInfoTVDB(seriesName, dvdIgnore=False, dvdMissing=False, quietFlag=False):
    series = []
    t = tvdb_api.Tvdb()
    show = t[seriesName]

    for season in show:
      for epnum in show[season]:
        episode = show[season][epnum]
        epid = episode['seasonnumber'] + "x" + episode['episodenumber'].zfill(2)
        epinfo = None
        if not dvdIgnore and episode[TVDB_DVDSEASON] and episode[TVDB_DVDEPNUM]:
          epinfo = [int(episode['seasonnumber']), int(episode['episodenumber']),
                    int(episode[TVDB_DVDSEASON]), float(episode[TVDB_DVDEPNUM])]
        elif not dvdIgnore and episode[TVDB_DVDEPNUM]:
          epinfo = [int(episode['seasonnumber']), int(episode['episodenumber']),
                    int(episode['seasonnumber']), float(episode[TVDB_DVDEPNUM])]
        else:
          if dvdMissing or dvdIgnore:
            epinfo = [int(episode['seasonnumber']), int(episode['episodenumber']),
                      int(episode['seasonnumber']), float(episode['episodenumber'])]
            if len(series) > 0:
              epnum = series[-1][DVDEPISODE]
              if len(series) > 1 and series[-1][DVDSEASON] == series[-2][DVDSEASON] \
                    and int(series[-1][DVDEPISODE]) - int(series[-2][DVDEPISODE]) > 1:
                epnum = int(series[-2][DVDEPISODE])
                epnum += 1
                epnum = float(epnum)
                series[-1][DVDEPISODE] = epnum
              if series[-1][ORIGDATE] == episode['firstaired']:
                epnum = str(epnum)
                idx = epnum.find('.')
                part = int(epnum[idx+1:])
                if part == 0:
                  part = 1
                  series[-1][DVDEPISODE] = float(epnum[:idx+1] + str(part))
                part += 1
                epinfo[DVDEPISODE] = float(epnum[:idx+1] + str(part))
          elif not quietFlag:
            print("No DVD info for")
            print(episode)
        if epinfo:
          epinfo.extend([episode['episodename'], episode['firstaired'],
                        episode['productioncode']])
          series.append(epinfo)

    return series
