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

import os, sys
import csv
import re
from enum import Enum, auto
import operator
import math
import collections
import re
import string
import unicodedata
from difflib import SequenceMatcher
from dataclasses import dataclass
import tvdb_api
import copy

# Words less than MINIMUM_WORD_LENGTH will be discarded automatically and don't
# need to be listed here
COMMON_WORDS = ["the", "and", "that"]
MINIMUM_WORD_LENGTH = 3

class EpisodeOrder(Enum):
  AIRED = auto()
  DVD = auto()
  ABSOLUTE = auto()

class EpisodeID:
  def __init__(self, val=None, *, season=None, episode=None, segment=None):
    if isinstance(val, str):
      start = val.split('x')
      season = int(start[0])
      segment = None
      if '.' in start[1]:
        idx = start[1].find('.')
        episode = int(start[1][:idx])
        segment = int(start[1][idx+1:])
      else:
        episode = int(start[1])
    elif isinstance(val, (list, tuple)):
      season, episode, segment = list(val) + [None]

    if isinstance(episode, float):
      segment = int((episode % 1) * 10)

    self.season = int(season)
    self.episode = int(episode)
    self.segment = None
    if segment is not None:
      self.segment = int(segment)
    return

  def asString(self, width=2, includeSegment=True):
    if width < 2:
      width = 2
    val = f"{self.season}x{self.episode:0{width}d}"
    if includeSegment and self.segment is not None:
      val += f".{self.segment}"
    return val

  def __repr__(self):
    return self.asString()

  def __eq__(self, other):
    return self.season == other.season \
      and self.episode == other.episode \
      and self.segment == other.segment

  def __lt__(self, other):
    return self.season < other.season \
      or self.episode < other.episode \
      or (self.segment is None and other.segment is not None) \
      or (other.segment is not None and self.segment < other.segment)

  def __hash__(self):
    return hash((self.season, self.episode, self.segment))

class EpisodeInfo:
  def __init__(self, airedID, dvdID, title, *, absoluteNum=None, airDate=None,
               productionCode=None, extra=None):
    self.airedID = airedID
    self.dvdID = dvdID
    self.absoluteNum = absoluteNum
    self.title = title
    self.airDate = airDate
    self.productionCode = productionCode
    self.extra = extra

    if title is None:
      raise ValueError("Bad title", title, airedID)
    if not isinstance(airedID, EpisodeID):
      raise ValueError("Bad airedID", airedID)
    if not isinstance(dvdID, EpisodeID):
      raise ValueError("Bad dvdID", type(dvdID), dvdID)
    return

  def asCSV(self):
    row = [self.airedID.asString(), self.dvdID.asString(), self.airDate, self.title,
           self.absoluteNum, self.extra]
    while row[-1] is None:
      del row[-1]
    return row

  def __repr__(self):
    return f"{self.airedID}/{self.dvdID}/{self.title}"

class EpisodeList:
  @dataclass
  class TitleMatch:
    episode: str
    seen: list
    words: int
    wordPercent: float
    lengthPercent: float
    usedPercent: float

  def __init__(self, episodes, key, minimumWordLength=3, commonWords=None):
    self.key = key
    self.episodes = sorted(episodes, key=operator.attrgetter(self.key))
    self.commonWords = commonWords
    self.minimumWordLength = minimumWordLength

    if self.commonWords is None:
      self.commonWords = set(COMMON_WORDS + self.mostCommon([x.title for x in self.episodes]))

    return

  def indexOf(self, episode):
    if isinstance(episode, list):
      episode = episode[0]
    return self.episodes.index(episode)

  def episodeNumbers(self, split=False):
    eps = []
    for e in self.episodes:
      eid = self.formatEpisodeID(e, self.key, fractional=split)
      if eid not in eps:
        eps.append(eid)
    return eps

  def formatEpisodeID(self, episode, key=None, fractional=False):
    num = 0
    if not key:
      key = self.key
    season = getattr(episode, key).season
    for row in self.episodes:
      if getattr(row, key).season == season:
        num += 1
    if num < 1:
      num = 1
    digits = int(math.floor(math.log(num, 10)) + 1)
    if digits < 2:
      digits = 2
    return getattr(episode, key).asString(width=digits, includeSegment=fractional)

  def findVideo(self, episode):
    guess = "\\b" + self.formatEpisodeID(episode.dvdID.season, episode.dvdID.episode) + "\\b"
    indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
    if not len(indices):
      guess = "\\b[sS]%02i[eE]%02i\\b" % (episode.dvdID.season, episode.dvdID.episode)
      indices = [i for i, x in enumerate(videos) if re.search(guess, x)]
    if len(indices):
      return videos[indices[0]]
    return None

  def renameVid(self, episode, filename, order, dryrunFlag):
    if isinstance(episode, list):
      title = ""
      for e in episode:
        t = e.title.strip()
        pstr = f" ({e.dvdID.segment})"
        if e.dvdID.segment and t.endswith(pstr):
          t = t[:-len(pstr)]
        if title != t:
          if len(title):
            title += " / "
          title += t
      episode = episode[0]
    else:
      title = episode.title.strip()
    title = re.sub("[:/]", "-", re.sub("[.!? ]+$", "", title))

    if order == EpisodeOrder.DVD:
      epid = self.formatEpisodeID(episode, 'dvdID')
    elif order == EpisodeOrder.ABSOLUTE:
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

  def titleToWords(self, title):
    ep_title = self.splitWords(title)
    if not len(ep_title):
      return None
    t_words = []
    for word in ep_title:
      if word in self.commonWords or len(word) < self.minimumWordLength:
        continue
      t_words.append(re.sub("[^0-9a-z]+", "", word))
    return t_words
    
  def compareTitle(self, episode, text, ocrWords):
    titleWords = self.titleToWords(episode.title)
    if not titleWords:
      return None

    m_words = []

    remain = titleWords.copy()
    for w in ocrWords:
      for tw in remain:
        pct_match = SequenceMatcher(None, tw, w).ratio()
        if pct_match > 0.9 or (tw in w and pct_match > 0.80):
          m_words.append(w)
          remain.remove(tw)
          break

    pct_words = len(m_words) / len(titleWords)
    pct_title = len(titleWords) / len(m_words) if len(m_words) else 0
    m_text = " ".join(m_words)
    pct_length = len(m_text) / len(episode.title)
    pct_used = len(m_text) / len(text)

    # if len(m_words):
    #   print("POSSIBLE MATCH\n"
    #         f"  Pct words: {pct_words}\n"
    #         f"  Pct title: {pct_title}\n",
    #         f"  Pct length: {pct_length}\n",
    #         f"  Pct used: {pct_used}\n",
    #         f"  m_words: {m_words}\n",
    #         f"  episode: {episode}\n",
    #         f"  m_text: {m_text}\n",
    #         f"  text: {text}\n")

    if (pct_length > 0.50 or pct_words == 1.0) \
       and (pct_title > 0.95 or pct_used > 0.50 or tstr[0] == '#'):
      #print("DID MATCH", episode.title, m_words)
      return EpisodeList.TitleMatch(episode, m_words, len(m_words),
                                    pct_words, pct_length, pct_used)

    #print("NOPE", pct_length, pct_used, episode.title[0] == '#')
    return None
    
  def findEpisode(self, epid, order=None, fractional=False):
    if not isinstance(epid, EpisodeID):
      epid = EpisodeID(epid)

    episode = None
    epcount = 0
    for row in self.episodes:
      rowid = getattr(row, self.key)
      if epid.season == rowid.season and epid.episode == rowid.episode \
         and (not fractional or epid.segment == rowid.segment):
        if not episode:
          episode = []
        episode.append(row)
        epcount += 1
    if epcount == 1:
      episode = episode[0]
    return episode

  def findEpisodeByTitle(self, text):
    words = [x for x in text.lower().split()
             if len(x) >= self.minimumWordLength and x not in self.commonWords]
    if not words:
      return None

    matches = []
    for row in self.episodes:
      tm = self.compareTitle(row, text, words)
      if tm is not None:
        matches.append(tm)

    if len(matches):
      matches.sort(key=lambda x: (x.usedPercent, x.wordPercent), reverse=True)
      return matches[0].episode

    return None

  def splitWords(self, line):
    output = line.translate(str.maketrans('', '', string.punctuation))
    output = unicodedata.normalize("NFKD", output).encode('ascii', 'ignore').decode("ascii")
    words = output.lower().split()
    words = [re.sub("[^0-9a-z]+", "", x) for x in words]
    words = [x for x in words if len(x) >= self.minimumWordLength and x not in COMMON_WORDS]
    if '' in words:
      raise ValueError(line, words)
    return words
  
  def mostCommon(self, titles):
    words = [self.splitWords(x) for x in titles]
    words = [x for xs in words for x in xs]
    counter = collections.Counter(words)
    common = counter.most_common()
    count = [x[1] for x in common]
    avg = sum(count) / len(count)
    most = [x[0] for x in common if x[1] >= avg * 3]
    return most

def loadEpisodeInfoFromCSV(path):
  CSV_EPISODE = 0
  CSV_DVDEP = 1
  CSV_ORIGDATE = 2
  CSV_TITLE = 3
  CSV_ABSOLUTE = 4
  series = []
  f = open(path, 'rU')
  try:
    reader = csv.reader(f)
    for row in reader:
      aired = EpisodeID(row[CSV_EPISODE])
      dvdep = row[CSV_DVDEP]
      if not re.match(".*x.*", dvdep):
        dvdep = aired + "." + dvdep
      dvd = EpisodeID(dvdep)
      anum = None
      if CSV_ABSOLUTE < len(row):
        anum = int(row[CSV_ABSOLUTE])
      info = EpisodeInfo(aired, dvd,
                         title=row[CSV_TITLE], airDate=row[CSV_ORIGDATE],
                         absoluteNum=anum)
      series.append(info)
  finally:
    f.close()
  return series

def loadEpisodeInfoFromTVDB(seriesName, dvdIgnore=False, dvdMissing=False, quietFlag=False,
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
      epdict = {
        'airedID': EpisodeID(season=int(episode['seasonnumber']),
                             episode=int(episode['episodenumber'])),
        'absoluteNum': anum,
        'title': episode['episodename'],
        'airDate': episode['firstaired'],
        'productionCode': episode['productioncode'],
      }

      if epdict['title'] is None:
        continue

      if not dvdIgnore and episode[TVDB_DVDSEASON] and episode[TVDB_DVDEPNUM]:
        epdict['dvdID'] = EpisodeID(season=int(episode[TVDB_DVDSEASON]),
                                    episode=float(episode[TVDB_DVDEPNUM]))
      elif not dvdIgnore and not episode[TVDB_DVDSEASON] and episode[TVDB_DVDEPNUM]:
        epdict['dvdID'] = EpisodeID(season=int(episode['seasonnumber']),
                                    episode=float(episode[TVDB_DVDEPNUM]))
      else:
        if dvdMissing or dvdIgnore:
          epdict['dvdID'] = EpisodeID(season=int(episode['seasonnumber']),
                                      episode=int(episode['episodenumber']))
          if len(series) > 0:
            epnum = series[-1].dvdID.episode
            if len(series) > 1 and series[-1].dvdID.season == series[-2].dvdID.season \
                  and series[-1].dvdID.episode - series[-2].dvdID.episode > 1:
              epnum = series[-2].dvdID.episode
              epnum += 1
              epnum = float(epnum)
              series[-1].dvdID.episode = epnum
            if series[-1].airDate == episode['firstaired']:
              epnum = str(epnum)
              idx = epnum.find('.')
              part = int(epnum[idx+1:])
              if part == 0:
                part = 1
                series[-1].dvdID.episode = float(epnum[:idx+1] + str(part))
              part += 1
              epdict['dvdID'].episode = float(epnum[:idx+1] + str(part))
        else:
          if not quietFlag:
            print("No DVD info for")
            print(episode)
          continue

      epinfo = EpisodeInfo(**epdict)
      series.append(epinfo)

  # thetvdb does not prevent duplicate DVD numbering, fix it
  series.sort(key=lambda x:(x.dvdID.season, x.dvdID.episode))
  for previous, current in zip(series, series[1:]):
    if previous.dvdID.season == current.dvdID.season \
       and previous.dvdID.episode >= current.dvdID.episode:
      part = int((previous.dvdID.episode * 10) % 10)
      if part == 0:
        part = 1
      previous.dvdID.episode = previous.dvdID.episode + part / 10
      current.dvdID.episode = previous.dvdID.episode + (part + 1) / 10
  return series
