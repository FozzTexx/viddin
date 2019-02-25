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

# This class is mostly just used to put all the functions in their own namespace
class viddin:
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
    width = os.get_terminal_size().columns
    pos = 0
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
          if c == 10:
            c = 13
          if c == 13 or width == 0 or pos < width - 2:
            sys.stdout.write(chr(c))
            pos += 1
            if c == 13:
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
      else:
        self.length = None
        self.chapters = []
        self.audio = []
        self.subtitles = []
        for track in info:
          if track['type'] == "video":
            if 'DURATION' in track:
              self.length = viddin.decodeTimecode(track['DURATION'])
          elif track['type'] == "audio":
            self.audio.append(track)
          elif track['type'] == "subtitles":
            self.subtitles.append(track)
      return
      
  @staticmethod
  def getDVDInfo(path):
    cmd = "lsdvd -asc -Oy %s 2>/dev/null" % (path)
    process = os.popen(cmd)
    pstr = process.read()
    process.close()
    pstr = pstr.replace("lsdvd = {", "{")
    tracks = ast.literal_eval(pstr)
    return tracks

  @staticmethod
  def getTitleInfoMKV(path, debugFlag=False):
    cmd = "mkvmerge -i -F json \"%s\"" % (path)
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
    info.length = tlen
    return info
    
  @staticmethod
  def getTitleInfo(path, title=None, debugFlag=False):
    tracks = []
    if title != None:
      dvdInfo = viddin.getDVDInfo(path)
      return viddin.TitleInfo(dvdInfo['track'][int(title) - 1], "dvd")

    _, ext = os.path.splitext(path)
    if ext == ".mkv":
      track = viddin.getTitleInfoMKV(path)
    else:
      track = viddin.TitleInfo([], None)
      track.length = viddin.getLength(path)
    return track

  class EpisodeInfo:
    def __init__(self, airedSeason, airedEpisode, dvdSeason, dvdEpisode,
                 title=None, airDate=None):
      self.airedSeason = airedSeason
      self.airedEpisode = airedEpisode
      self.dvdSeason = dvdSeason
      self.dvdEpisode = dvdEpisode
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
      return episodes.index(episode)
    
    def formatEpisodeID(self, episode):
      num = 0
      season = getattr(episode, self.seasonKey)
      epnum = getattr(episode, self.episodeKey)
      for row in self.episodes:
        if getattr(row, self.seasonKey) == season:
          num += 1
      if num < 1:
        num = 1
      digits = int(math.floor(math.log(num, 10)) + 1)
      if digits < 2:
        digits = 2
      epid = "%%ix%%0%ii" % digits
      return epid % (season, epnum)

    def findVideo(self, episode):
      guess = "\\b" + formatEpisodeID(episode.dvdSeason, episode.dvdEpisode) + "\\b"
      indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
      if not len(indices):
        guess = "\\b[sS]%02i[eE]%02i\\b" % (episode.dvdSeason, episode.dvdEpisode)
        indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
      if len(indices):
        return videos[indices[0]]
      return None

    def findEpisode(self, epid):
      if type(epid) is int:
        epid = self.formatEpisodeID(self.episodes[epid])

      episode = None
      epcount = 0
      dvdnum = re.split(" *x *", epid)
      dvdseason = int(re.sub("[^0-9]*", "", dvdnum[0]));
      dvdepisode = int(re.sub("[^0-9]*", "", dvdnum[1]));
      for row in self.episodes:
        if dvdseason == getattr(row, self.seasonKey) \
              and dvdepisode == getattr(row, self.episodeKey):
          if not episode:
            episode = []
          episode.append(row)
          epcount += 1
      if epcount == 1:
        episode = episode[0]
      return episode
    
    def renameVid(self, episode, filename, dvdorderFlag, dryrunFlag):
      epid = self.formatEpisodeID(episode)

      if not filename:
        filename = findVideo(episode)

      if filename:
        video, ext = os.path.splitext(filename)

        if episode == episode:
          title = re.sub("[:/]", "-", re.sub("[.!?]+$", "", episode.title.strip()))
        else:
          title = ""
          for ep in episode:
            if len(title):
              title += " / "
            title += ep.title
        title = re.sub("[:/]", "-", re.sub("[.!?]+$", "", title))

        if dvdorderFlag:
          part = int((episode.dvdEpisode * 10) % 10)
          if part and title.endswith(" (" + str(part) + ")"):
            title = title[:-4]
        eptitle = "%s %s%s" % (epid, title, ext)
        if filename != eptitle:
          if not os.path.isfile(eptitle) or args.dryrun:
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
        info = viddin.EpisodeInfo(int(epnum[0]), int(epnum[1]),
                                  int(dvdnum[0]), float(dvdnum[1]),
                           row[CSV_TITLE], row[CSV_ORIGDATE])
        series.append(info)
    finally:
      f.close()
    return series

  @staticmethod
  def loadEpisodeInfoTVDB(seriesName, dvdIgnore=False, dvdMissing=False, quietFlag=False):
    TVDB_DVDSEASON = "dvd_season"
    TVDB_DVDEPNUM = "dvd_episodenumber"
    if float(tvdb_api.__version__) >= 2.0:
      TVDB_DVDSEASON = "dvdSeason"
      TVDB_DVDEPNUM = "dvdEpisodeNumber"

    series = []
    t = tvdb_api.Tvdb()
    show = t[seriesName]

    for season in show:
      for epnum in show[season]:
        episode = show[season][epnum]
        epid = episode['seasonnumber'] + "x" + episode['episodenumber'].zfill(2)
        epinfo = None
        if not dvdIgnore and episode[TVDB_DVDSEASON] and episode[TVDB_DVDEPNUM]:
          epinfo = viddin.EpisodeInfo(int(episode['seasonnumber']),
                                      int(episode['episodenumber']),
                                      int(episode[TVDB_DVDSEASON]),
                                      float(episode[TVDB_DVDEPNUM]))
        elif not dvdIgnore and episode[TVDB_DVDEPNUM]:
          epinfo = viddin.EpisodeInfo(int(episode['seasonnumber']),
                                      int(episode['episodenumber']),
                                      int(episode['seasonnumber']),
                                      float(episode[TVDB_DVDEPNUM]))
        else:
          if dvdMissing or dvdIgnore:
            epinfo = viddin.EpisodeInfo(int(episode['seasonnumber']),
                                        int(episode['episodenumber']),
                                        int(episode['seasonnumber']),
                                        float(episode['episodenumber']))
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
