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
import tvdb_api
import operator
import math
import ast
import tempfile
import csv
import curses
import stat

# This class is mostly just used to put all the functions in their own namespace
class viddin:
  ORDER_AIRED = 1
  ORDER_DVD = 2
  ORDER_ABSOLUTE = 3
  
  didCursesInit = False
  @staticmethod
  def initCurses():
    if not viddin.didCursesInit:
      curses.setupterm()
      viddin.clearEOL = curses.tigetstr("el")
      if viddin.clearEOL:
        viddin.clearEOL = viddin.clearEOL.decode()
      else:
        viddin.clearEOL = ""
      viddin.didCursesInit = True
      return
    
  @staticmethod
  def isint(s):
    try:
      int(s)
      return True
    except ValueError:
      return False

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
  def writeChapters(path, chapters):
    _, ext = os.path.splitext(path)
    if ext == ".mkv":
      cfile, cfname = tempfile.mkstemp()
      for idx in range(len(chapters)):
        os.write(cfile, bytes("CHAPTER%02i=%s\n" % (idx + 1,
                                                    viddin.formatChapter(chapters[idx])),
                              'UTF-8'))
        os.write(cfile, bytes("CHAPTER%02iNAME=Chapter %i\n" % (idx + 1, idx + 1), 'UTF-8'))
      os.close(cfile)

      cmd = "mkvpropedit -c %s \"%s\"" % (cfname, path.replace("\"", "\\\""))
      os.system(cmd)
      os.remove(cfname)
    else:
      vlen = viddin.getLength(path)
      if vlen is not None:
        if abs(vlen - chapters[-1]) > 1:
          chapters = chapters.copy()
          chapters.append(vlen)
        cfile, cfname = tempfile.mkstemp()
        os.write(cfile, bytes(";FFMETADATA1\n", 'UTF-8'))
        for i in range(len(chapters) - 1):
          os.write(cfile, bytes("[CHAPTER]\n", 'UTF-8'))
          os.write(cfile, bytes("TIMEBASE=1/1000\n", 'UTF-8'))
          os.write(cfile, bytes("START=%i\n" % (int(chapters[i] * 1000)), 'UTF-8'))
          os.write(cfile, bytes("END=%i\n" % (int(chapters[i + 1] * 1000)), 'UTF-8'))
          os.write(cfile, bytes("title=Chapter %i\n" % (i + 1), 'UTF-8'))
        os.close(cfile)

        dpath = os.path.dirname(path)
        tf = tempfile.NamedTemporaryFile(suffix=ext, dir=dpath, delete=False)
        cmd = "ffmpeg -y -i \"%s\" -i %s -map_metadata 1 -movflags disable_chpl" \
              " -codec copy -map 0 \"%s\"" % \
              (path.replace("\"", "\\\""), cfname, tf.name.replace("\"", "\\\""))
        stat = viddin.runCommand(cmd)
        if stat == 0:
          os.rename(tf.name, path)
        else:
          os.remove(tf.name)
        os.remove(cfname)
    return

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
  def runCommand(cmd):
    viddin.initCurses()
    width = os.get_terminal_size().columns
    pos = 0
    err = None
    master, slave = pty.openpty()
    with subprocess.Popen(cmd, shell=True, stdin=slave, stdout=slave, stderr=slave,
                         close_fds=True) as p:
      m = os.fdopen(master, "rb")
      os.close(slave)
      try:
        while True:
          c = list(m.read(1))[0]
          if c > 127:
            continue
          if c == 27:
            c = list(m.read(1))[0]
            if c == '[':
              c = list(m.read(1))[0]
              if c == 'K':
                continue
          if c == 10:
            c = 13
          if (c == 13 and pos > 0) or width == 0 or pos < width - 2:
            if pos == 0:
              sys.stdout.write(viddin.clearEOL)
            sys.stdout.write(chr(c))
            pos += 1
            if c == 13:
              pos = 0
          sys.stdout.flush()
      except OSError:
        pass
      os.close(master)
      p.wait()
      err = p.returncode
    return err

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
  def bestSilence(best, silence):
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

  class TitleInfo:
    def __init__(self, info, infoType):
      if infoType == "dvd":
        self.length = info['length']
        self.chapters = [0]
        for idx in range(len(info['chapter'])):
          chap = info['chapter'][idx]
          pos = self.chapters[-1]
          pos += chap['length']
          self.chapters.append(pos)
        self.audio = info['audio']
        self.subtitles = info['subp']
        self.video = []
      else:
        self.length = None
        self.chapters = []
        self.audio = []
        self.subtitles = []
        self.video = []
        for track in info:
          if 'properties' in track:
            track = {**track, **track['properties']}
          if track['type'] == "video":
            if 'DURATION' in track:
              self.length = viddin.decodeTimecode(track['DURATION'])
            self.video.append(track)
          elif track['type'] == "audio":
            self.audio.append(track)
          elif track['type'] == "subtitles":
            self.subtitles.append(track)
      return

    def __repr__(self):
      return "TitleInfo %0.3f" % (self.length)
      
  @staticmethod
  def getDVDInfo(path):
    process = subprocess.Popen(["lsdvd", "-asc", "-Oy", path], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    pstr = process.stdout.read()
    process.stdout.close()
    pstr = pstr.decode("utf-8", "backslashreplace")
    pstr = pstr.replace("lsdvd = {", "{").strip()
    tracks = None
    if len(pstr) and pstr[-1] == '}':
      tracks = ast.literal_eval(pstr)
    else:
      print("bad track info", pstr)
    return tracks

  @staticmethod
  def getLength(filename, title=None, chapters=None, debugFlag=False):
    cmd = "ffprobe -v error -show_entries format=duration -of" \
          " default=noprint_wrappers=1:nokey=1 \"%s\"" % (filename)
    if debugFlag:
      print(cmd)
    process = os.popen(cmd)
    jstr = process.read()
    process.close()
    try:
      tlen = float(jstr)
    except ValueError:
      tlen = 0

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
  def getResolution(filename, debugFlag=False):
    cmd = "ffprobe -v error -select_streams v:0 -show_entries stream=width,height" \
          " -of csv=s=x:p=0 \"%s\"" % (filename)
    if debugFlag:
      print(cmd)
    process = os.popen(cmd)
    res = process.read()
    process.close()
    res = res.split('x')
    return (int(res[0]), int(res[1]))

  @staticmethod
  def getTitleInfoMKV(path, debugFlag=False):
    cmd = "mkvmerge -i -F json \"%s\"" % (path)
    if debugFlag:
      print(cmd)
    process = os.popen(cmd)
    jstr = process.read()
    process.close()
    jinfo = json.loads(jstr)
    if 'tracks' not in jinfo:
      return None

    tracks = []
    for track in jinfo['tracks']:
      info = track.copy()
      info['rv_track_id'] = track['id']
      if 'properties' in track:
        info.update(track['properties'])
      tracks.append(info)

    cmd = "mkvextract tags \"%s\" 2>/dev/null" % (path)
    process = os.popen(cmd)
    xstr = process.read()
    process.close()
    xstr = xstr.strip()
    if len(xstr) and not xstr.startswith("Error:"):
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

    info = viddin.TitleInfo(tracks, None)
    info.chapters = viddin.loadChapters(path)

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
    if not tlen:
      tlen = viddin.getLength(path)
    info.length = tlen
    return info

  @staticmethod
  def isDVD(path):
    mode = os.stat(path).st_mode
    if stat.S_ISBLK(mode) or stat.S_ISDIR(mode):
      return True
    _, ext = os.path.splitext(path)
    if ext.lower() == ".iso":
      return True
    return False
    
  @staticmethod
  def getTitleInfo(path, title=None, debugFlag=False):
    if title != None:
      dvdInfo = viddin.getDVDInfo(path)
      if not dvdInfo is None:
        return viddin.TitleInfo(dvdInfo['track'][int(title) - 1], "dvd")
      print("Failed to get title info", title)
      return None

    # ffprobe -v quiet -print_format json -show_format -show_streams
    
    _, ext = os.path.splitext(path)
    if True or ext == ".mkv":
      track = viddin.getTitleInfoMKV(path)
    else:
      track = viddin.TitleInfo([], None)
      track.length = viddin.getLength(path)
    return track

  class EpisodeInfo:
    def __init__(self, airedSeason, airedEpisode, dvdSeason, dvdEpisode,
                 absoluteNum=None, title=None, airDate=None):
      self.airedSeason = airedSeason
      self.airedEpisode = airedEpisode
      self.dvdSeason = dvdSeason
      self.dvdEpisode = dvdEpisode
      self.absoluteNum = absoluteNum
      self.title = title
      self.airDate = airDate
      return

    def description(self):
      return "%i %i %i %0.1f %s %s" % (self.airedSeason, self.airedEpisode, self.dvdSeason,
                                       self.dvdEpisode, self.title, self.airDate)

  class EpisodeList:
    def __init__(self, episodes, seasonKey, episodeKey):
      self.episodes = sorted(episodes, key=operator.attrgetter(seasonKey, episodeKey))
      self.seasonKey = seasonKey
      self.episodeKey = episodeKey
      return

    def indexOf(self, episode):
      if isinstance(episode, list):
        episode = episode[0]
      return self.episodes.index(episode)

    def episodeNumbers(self):
      eps = []
      for e in self.episodes:
        eid = self.formatEpisodeID(e, self.seasonKey, self.episodeKey)
        if eid not in eps:
          eps.append(eid)
      return eps
      
    def formatEpisodeID(self, episode, skey=None, ekey=None):
      num = 0
      if not skey:
        skey = self.seasonKey
      if not ekey:
        ekey = self.episodeKey
      epnum = getattr(episode, ekey)
      if isinstance(skey, int):
        season = skey
        num = len(self.episodes)
      else:
        season = getattr(episode, skey)
        for row in self.episodes:
          if getattr(row, skey) == season:
            num += 1
      if num < 1:
        num = 1
      digits = int(math.floor(math.log(num, 10)) + 1)
      if digits < 2:
        digits = 2
      epid = "%%ix%%0%ii" % digits
      return epid % (season, epnum)

    def findVideo(self, episode):
      guess = "\\b" + self.formatEpisodeID(episode.dvdSeason, episode.dvdEpisode) + "\\b"
      indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
      if not len(indices):
        guess = "\\b[sS]%02i[eE]%02i\\b" % (episode.dvdSeason, episode.dvdEpisode)
        indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
      if len(indices):
        return videos[indices[0]]
      return None

    def findEpisode(self, epid, order=None):
      if type(epid) is int:
        if order == viddin.ORDER_DVD:
          epid = self.formatEpisodeID(self.episodes[epid], "dvdSeason", "dvdEpisode")
        elif order == viddin.ORDER_ABSOLUTE:
          epid = self.formatEpisodeID(self.episode[epid], 1, "absoluteNum")
        else:
          epid = self.formatEpisodeID(self.episodes[epid])

      episode = None
      epcount = 0
      dvdnum = re.split(" *x *", epid)
      dvdseason = int(re.sub("[^0-9]*", "", dvdnum[0]));
      dvdepisode = int(re.sub("[^0-9]*", "", dvdnum[1]));
      for row in self.episodes:
        if dvdseason == getattr(row, self.seasonKey) \
              and dvdepisode == int(getattr(row, self.episodeKey)):
          if not episode:
            episode = []
          episode.append(row)
          epcount += 1
      if epcount == 1:
        episode = episode[0]
      return episode
    
    def renameVid(self, episode, filename, order, dryrunFlag):
      if isinstance(episode, list):
        title = ""
        for e in episode:
          t = e.title.strip()
          part = int((e.dvdEpisode * 10) % 10)
          pstr = " (" + str(part) + ")"
          if part and t.endswith(pstr):
            t = t[:-len(pstr)]
          if title != t:
            if len(title):
              title += " / "
            title += t
        episode = episode[0]
      else:
        title = episode.title.strip()
      title = re.sub("[:/]", "-", re.sub("[.!? ]+$", "", title))
        
      if order == viddin.ORDER_DVD:
        epid = self.formatEpisodeID(episode, "dvdSeason", "dvdEpisode")
      elif order == viddin.ORDER_ABSOLUTE:
        epid = self.formatEpisodeID(episode, 1, "absoluteNum")
      else:
        epid = self.formatEpisodeID(episode)

      if not filename:
        filename = findVideo(episode)

      if filename:
        video, ext = os.path.splitext(filename)
        eptitle = "%s %s%s" % (epid, title, ext)
        if filename != eptitle:
          if not os.path.isfile(eptitle) or dryrunFlag:
            if not dryrunFlag:
              os.rename(filename, eptitle)
            print(filename + " to " + eptitle)
          else:
            print("Already exists! " + eptitle)
      return filename

  @staticmethod
  def loadEpisodeInfoCSV(filename):
    CSV_EPISODE = 0
    CSV_DVDEP = 1
    CSV_ORIGDATE = 2
    CSV_TITLE = 3
    CSV_ABSOLUTE = 4
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
        anum = None
        if CSV_ABSOLUTE < len(row):
          anum = int(row[CSV_ABSOLUTE])
        info = viddin.EpisodeInfo(int(epnum[0]), int(epnum[1]),
                                  int(dvdnum[0]), float(dvdnum[1]),
                                  title=row[CSV_TITLE], airDate=row[CSV_ORIGDATE],
                                  absoluteNum=anum)
        series.append(info)
    finally:
      f.close()
    return series

  @staticmethod
  def loadEpisodeInfoTVDB(seriesName, dvdIgnore=False, dvdMissing=False, quietFlag=False,
                          interactiveFlag=False):
    TVDB_DVDSEASON = "dvd_season"
    TVDB_DVDEPNUM = "dvd_episodenumber"
    if float(tvdb_api.__version__) >= 2.0:
      TVDB_DVDSEASON = "dvdSeason"
      TVDB_DVDEPNUM = "dvdEpisodeNumber"

    series = []
    t = tvdb_api.Tvdb(interactive=interactiveFlag)
    show = t[seriesName]

    for season in show:
      for epnum in show[season]:
        episode = show[season][epnum]
        epid = episode['seasonnumber'] + "x" + episode['episodenumber'].zfill(2)
        epinfo = None
        anum = episode['absoluteNumber']
        if anum:
          anum = int(anum)
        else:
          anum = 0
        if not dvdIgnore and episode[TVDB_DVDSEASON] and episode[TVDB_DVDEPNUM]:
          epinfo = viddin.EpisodeInfo(int(episode['seasonnumber']),
                                      int(episode['episodenumber']),
                                      int(episode[TVDB_DVDSEASON]),
                                      float(episode[TVDB_DVDEPNUM]),
                                      absoluteNum=anum)
        elif not dvdIgnore and episode[TVDB_DVDEPNUM]:
          epinfo = viddin.EpisodeInfo(int(episode['seasonnumber']),
                                      int(episode['episodenumber']),
                                      int(episode['seasonnumber']),
                                      float(episode[TVDB_DVDEPNUM]),
                                      absoluteNum=anum)
        else:
          if dvdMissing or dvdIgnore:
            epinfo = viddin.EpisodeInfo(int(episode['seasonnumber']),
                                        int(episode['episodenumber']),
                                        int(episode['seasonnumber']),
                                        float(episode['episodenumber']),
                                        absoluteNum=anum)
            if len(series) > 0:
              epnum = series[-1].dvdEpisode
              if len(series) > 1 and series[-1].dvdSeason == series[-2].dvdSeason \
                    and int(series[-1].dvdEpisode) - int(series[-2].dvdEpisode) > 1:
                epnum = int(series[-2].dvdEpisode)
                epnum += 1
                epnum = float(epnum)
                series[-1].dvdEpisode = epnum
              if series[-1].airDate == episode['firstaired']:
                epnum = str(epnum)
                idx = epnum.find('.')
                part = int(epnum[idx+1:])
                if part == 0:
                  part = 1
                  series[-1].dvdEpisode = float(epnum[:idx+1] + str(part))
                part += 1
                epinfo.dvdEpisode = float(epnum[:idx+1] + str(part))
          elif not quietFlag:
            print("No DVD info for")
            print(episode)
        if epinfo:
          epinfo.title = episode['episodename']
          epinfo.airDate = episode['firstaired']
          epinfo.productionCode = episode['productioncode']
          series.append(epinfo)

    return series
