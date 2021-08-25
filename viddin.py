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
import io
from dvdlang import dvdLangISO
from collections import namedtuple

# This class is mostly just used to put all the functions in their own namespace
class viddin:
  
  ORDER_AIRED = 1
  ORDER_DVD = 2
  ORDER_ABSOLUTE = 3

  Chapter = namedtuple("Chapter", ["position", "name"])
  
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
    tc = tc.replace(',', '.')
    fraction = 0
    if re.match(".*[.][0-9]+$", tc):
      parts = re.split("[.]", tc)
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
  def runCommand(cmd, debugFlag=False):
    do_shell = True
    if isinstance(cmd, (list, tuple)):
      do_shell = False

    if debugFlag:
      err = subprocess.call(cmd)
    else:
      viddin.initCurses()
      width = os.get_terminal_size().columns
      pos = 0
      err = None
      master, slave = pty.openpty()
      with subprocess.Popen(cmd, shell=do_shell, stdin=slave, stdout=slave, stderr=slave,
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
      self.tracks = []
      self.tracks.extend(self.video)
      self.tracks.extend(self.audio)
      self.tracks.extend(self.subtitles)

      if len(self.tracks) and 'rv_track_id' in self.tracks[0]:
        self.audio.sort(key=lambda x:x['rv_track_id'])
        self.subtitles.sort(key=lambda x:x['rv_track_id'])
        self.video.sort(key=lambda x:x['rv_track_id'])
        self.tracks.sort(key=lambda x:x['rv_track_id'])
      return

    def __repr__(self):
      return "TitleInfo %0.3f" % (self.length)
      
  @staticmethod
  def getDVDInfo(path, debugFlag=False):
    cmd = ["lsdvd", "-asc", "-Oy", path]
    if debugFlag:
      print(cmd)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
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

    for trk in tracks['track']:
      # the video track is number 0
      rv_track_id = 1
      for ttype in ('audio', 'subp'):
        for strk in trk[ttype]:
          strk['rv_track_id'] = rv_track_id
          strk['type'] = ttype if ttype != 'subp' else 'subtitles'
          if strk['langcode'] in dvdLangISO:
            strk['language'] = dvdLangISO[strk['langcode']]
          rv_track_id += 1
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

    def __repr__(self):
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

    def episodeNumbers(self, split=False):
      eps = []
      for e in self.episodes:
        eid = self.formatEpisodeID(e, self.seasonKey, self.episodeKey, fractional=split)
        if eid not in eps:
          eps.append(eid)
      return eps
      
    def formatEpisodeID(self, episode, skey=None, ekey=None, fractional=False):
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
      eid_str = epid % (season, epnum)
      if fractional:
        eid_str += ".%i" % (epnum * 10 - int(epnum) * 10)
      return eid_str

    def findVideo(self, episode):
      guess = "\\b" + self.formatEpisodeID(episode.dvdSeason, episode.dvdEpisode) + "\\b"
      indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
      if not len(indices):
        guess = "\\b[sS]%02i[eE]%02i\\b" % (episode.dvdSeason, episode.dvdEpisode)
        indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
      if len(indices):
        return videos[indices[0]]
      return None

    def findEpisode(self, epid, order=None, fractional=False):
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
      if fractional:
        dvdepisode = float(re.sub("[^0-9.]*", "", dvdnum[1]));
      for row in self.episodes:
        if dvdseason == getattr(row, self.seasonKey) \
              and (dvdepisode == int(getattr(row, self.episodeKey))
                   or (fractional and dvdepisode == getattr(row, self.episodeKey))):
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
    vers = tvdb_api.__version__.split('.')
    if int(vers[0]) >= 2:
      TVDB_DVDSEASON = "dvdSeason"
      TVDB_DVDEPNUM = "dvdEpisodeNumber"

    series = []
    old_stdout = sys.stdout
    sys.stdout = open("/dev/tty", "w")
    t = tvdb_api.Tvdb(interactive=interactiveFlag)
    show = t[seriesName]
    sys.stdout = old_stdout

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

    # thetvdb does not prevent duplicate DVD numbering, fix it
    series.sort(key=lambda x:(x.dvdSeason, x.dvdEpisode))
    for previous, current in zip(series, series[1:]):
      if previous.dvdSeason == current.dvdSeason \
         and previous.dvdEpisode >= current.dvdEpisode:
        part = int((previous.dvdEpisode * 10) % 10)
        if part == 0:
          part = 1
        previous.dvdEpisode = int(previous.dvdEpisode) + part / 10
        current.dvdEpisode = int(previous.dvdEpisode) + (part + 1) / 10
    return series

  @staticmethod
  def uniqueFile(path, extension=None):
    dest, ext = os.path.splitext(path)
    if not extension:
      extension = ext
    if extension[0] != '.':
      extension = "." + extension
    counter = None
    upath = dest + extension
    while os.path.exists(upath):
      if not counter:
        counter = 1
      counter += 1
      upath = dest + str(counter) + extension
    return upath

  class VideoSpec:
    def __init__(self, path, titleNumber=None):
      self.path = path
      self.titleNumber = titleNumber
      return

    def isDVD(self):
      mode = os.stat(self.path).st_mode
      if stat.S_ISBLK(mode) or stat.S_ISDIR(mode):
        return True
      _, ext = os.path.splitext(self.path)
      if ext.lower() == ".iso":
        return True
      return False

    def getTitleInfo(self, debugFlag=False):
      if self.titleNumber is not None or self.isDVD():
        dvdInfo = viddin.getDVDInfo(self.path, debugFlag=debugFlag)
        if not dvdInfo is None:
          return viddin.TitleInfo(dvdInfo['track'][self.titleNumber - 1], "dvd")
        print("Failed to get title info", self.titleNumber)
        return None

      # ffprobe -v quiet -print_format json -show_format -show_streams

      _, ext = os.path.splitext(self.path)
      if True or ext == ".mkv":
        track = self.getTitleInfoMKV(debugFlag=debugFlag)
      else:
        track = viddin.TitleInfo([], None)
        track.length = self.getLength()
      return track

    def getTitleInfoMKV(self, debugFlag=False):
      cmd = "mkvmerge -i -F json \"%s\"" % (self.path)
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
        info['rv_track_id'] = int(track['id'])
        if 'properties' in track:
          info.update(track['properties'])
        tracks.append(info)

      cmd = "mkvextract tags \"%s\" 2>/dev/null" % (self.path)
      if debugFlag:
        print(cmd)
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
            if isinstance(xi2, str):
              continue
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
              elif 'String' in xi3 and 'Name' in xi3:
                xdict[xi3['Name']] = xi3['String']
            xlist.append(xdict)

        for track in xlist:
          if 'TrackUID' in track:
            tt = viddin.trackWithUid(track['TrackUID'], tracks)
            if tt:
              tt.update(track)

      info = viddin.TitleInfo(tracks, None)
      info.chapters = self.loadChapters()

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
        tlen = viddin.getLength(self.path)
      info.length = tlen
      return info

    def startEndForChapters(self, chapters, debugFlag=False):
      if '-' in chapters:
        chaps = chapters.split("-")
      else:
        chaps = [chapters, chapters]
      chaptimes = self.loadChapters()
      chaptimes.append(viddin.Chapter(self.getTitleInfo(debugFlag=debugFlag).length, "end"))
      start = chaptimes[int(chaps[0]) - 1]
      end = chaptimes[int(chaps[1])]
      return start.position, end.position

    def loadChapters(self, debugFlag=False):
      chapters = []
      if self.titleNumber != None or self.isDVD():
        dvdInfo = viddin.getDVDInfo(self.path, debugFlag=debugFlag)
        chaps = dvdInfo['track'][self.titleNumber - 1]['chapter']
        chapters.append(0)
        offset = 0
        for c in chaps:
          offset += c['length']
          chapters.append(offset)
      else:
        cmd = ["ffprobe", "-i", self.path, "-print_format", "json", "-show_chapters"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
        pstr = process.stdout.read()
        process.stdout.close()
        jinfo = json.loads(pstr)

        for idx, chp in enumerate(jinfo['chapters']):
          begin = float(chp['start_time'])
          name = "Chapter %i" % (idx + 1)
          if 'tags' in chp and 'title' in chp['tags']:
            name = chp['tags']['title']
          chapters.append(viddin.Chapter(begin, name))
      return chapters

    def writeChapters(self, chapters):
      _, ext = os.path.splitext(self.path)
      if ext == ".mkv":
        cfile, cfname = tempfile.mkstemp()
        for idx in range(len(chapters)):
          if isinstance(chapters[idx], (int, float)):
            pos = chapters[idx]
            name = "Chapter %i" % (idx + 1)
          else:
            pos = chapters[idx].position
            name = chapters[idx].name
          os.write(cfile, bytes("CHAPTER%02i=%s\n" % (idx + 1, viddin.formatChapter(pos)),
                                'UTF-8'))
          os.write(cfile, bytes("CHAPTER%02iNAME=%s\n" % (idx + 1, name), 'UTF-8'))
        os.close(cfile)

        cmd = "mkvpropedit -c %s \"%s\"" % (cfname, self.path.replace("\"", "\\\""))
        os.system(cmd)
        os.remove(cfname)
      else:
        vlen = viddin.getLength(self.path)
        if vlen is not None:
          if abs(vlen - chapters[-1]) > 1:
            chapters = chapters.copy()
            chapters.append(vlen)
          cfile, cfname = tempfile.mkstemp()
          os.write(cfile, bytes(";FFMETADATA1\n", 'UTF-8'))
          for idx in range(len(chapters) - 1):
            if isinstance(chapters[idx], (int, float)):
              pos = chapters[idx]
              npos = chapters[idx+1]
              name = "Chapter %i" % (idx + 1)
            else:
              pos = chapters[idx].position
              npos = chapters[idx+1].position
              name = chapters[idx].name

            os.write(cfile, bytes("[CHAPTER]\n", 'UTF-8'))
            os.write(cfile, bytes("TIMEBASE=1/1000\n", 'UTF-8'))
            os.write(cfile, bytes("START=%i\n" % (int(pos * 1000)), 'UTF-8'))
            os.write(cfile, bytes("END=%i\n" % (int(npos * 1000)), 'UTF-8'))
            os.write(cfile, bytes("title=%s\n" % (name), 'UTF-8'))
          os.close(cfile)

          dpath = os.path.dirname(self.path)
          tf = tempfile.NamedTemporaryFile(suffix=ext, dir=dpath, delete=False)
          cmd = "ffmpeg -y -i \"%s\" -i %s -map_metadata 1 -movflags disable_chpl" \
                " -codec copy -map 0 \"%s\"" % \
                (self.path.replace("\"", "\\\""), cfname, tf.name.replace("\"", "\\\""))
          stat = viddin.runCommand(cmd)
          if stat == 0:
            os.rename(tf.name, self.path)
          else:
            os.remove(tf.name)
          os.remove(cfname)
      return

    def extractDVDSubtitle(self, dest, trackNum, start, end, lang, debugFlag=False):
      path, ext = os.path.splitext(dest)
      ts_path = path + ".mkv"
      trk_source = viddin.uniqueFile(ts_path)
      # FIXME - look at trackNum and figure out if it needs subtitle
      #         flags or audio flags or something else
      cmd = ["HandBrakeCLI", "-w", "1",
             "-i", self.path,
             "--title", str(self.titleNumber),
             "-o", trk_source]

      if trackNum is None:
        # This will get closed caption subtitles with ccextractor if they are available
        cmd.extend(["--subtitle-lang-list", lang, "--all-subtitles"])
      else:
        cmd.extend(["--subtitle", str(trackNum)])

      if start is not None:
        cmd.extend(["--start-at", "seconds:" + str(start)])
      if end is not None:
        stop = end
        if start is not None:
          stop -= start
        cmd.extend(["--stop-at", "seconds:" + str(stop)])

      # if args.chapters:
      #   cmd += " --chapters " + args.chapters
      if debugFlag:
        print(" ".join(cmd))
        print(cmd)
      err = viddin.runCommand(cmd)

      if not os.path.exists(trk_source):
        print("Failed to extract track")
        exit(1)
      return trk_source

    def parseTrackDescriptors(self, tracks):
      parsed = []
      for trk in tracks:
        if isinstance(trk, int):
          tnum = trk
          ttitle = None
        else:
          sep = trk.find(':')
          if sep >= 0:
            tnum = trk[:sep]
            ttitle = trk[sep+1:]
          else:
            tnum = trk
            ttitle = None
        parsed.append({'number': tnum, 'title': ttitle})
      tinfo = self.getTitleInfo()
      for trk in parsed:
        tnum = trk['number']
        if isinstance(tnum, str) and tnum[0].isalpha():
          ttype = tnum[0].lower()
          tnum = int(tnum[1:])
          if ttype == 'a':
            tnum = tinfo.audio[tnum]['rv_track_id']
          elif ttype == 'v':
            tnum = tinfo.video[tnum]['rv_track_id']
          elif ttype == 's':
            tnum = tinfo.subtitles[tnum]['rv_track_id']
        else:
          for idx, t2 in enumerate(tinfo.tracks):
            if t2['rv_track_id'] == tnum:
              #print("FOUND", idx, tnum, t2)
              tnum = idx
              break
        trk['number'] = tnum
      return parsed
          
    def extractTrack(self, dest, trackNum, start, end, lang, debugFlag=False):
      # If start/end were specified, the original file has to be
      # split just to split the subs, otherwise the subs will be
      # misaligned.

      path, ext = os.path.splitext(dest)
      trk_source = self.path
      if self.isDVD():
        # FIXME - what about audio tracks?
        trk_source = self.extractDVDSubtitle(dest, trackNum, start, end, lang, debugFlag)
        sub_track = viddin.VideoSpec(trk_source)
        tinfo = sub_track.getTitleInfo()
        subs = tinfo.subtitles
        track_num = subs[0]['rv_track_id']
      else:
        if start is not None or end is not None:
          ts_path = path + ".mkv"
          trk_source = viddin.uniqueFile(ts_path)

          if start is None:
            start = 0
          if end is None:
            end = ""  
          cmd = "mkvmerge --split parts:%s-%s -o \"%s\" \"%s\"" % \
              (viddin.formatTimecode(start), viddin.formatTimecode(end), trk_source, self.path)
          if debugFlag:
            print(cmd)
          viddin.runCommand(cmd)

      # FIXME - change extension based on track type/encoding
      trk_ext = "sub"
      trk_path = "%s_%i.%s" % (path, trackNum, trk_ext)
      cmd = "mkvextract tracks \"%s\" %i:\"%s\"" % (trk_source, trackNum, trk_path)
      if debugFlag:
        print(cmd)
      err = viddin.runCommand(cmd)
      if err:
        print("Failed to extract")
        exit(1)
      if trk_source != self.path:
        os.remove(trk_source)

      idx_path = "%s_%i.idx" % (path, trackNum)
      if os.path.exists(idx_path):
        trk_path = [idx_path, trk_path]
        
      return viddin.TrackSpec(trk_path, None)

  class TrackSpec:
    def __init__(self, path, trackNumber):
      self.path = path
      self.trackNumber = trackNumber
      return

    def remove(self):
      if isinstance(self.path, list):
        for p in self.path:
          os.remove(p)
      else:
        os.remove(self.path)
      return

    @property
    def primary(self):
      if isinstance(self.path, list):
        return self.path[0]
      return self.path

