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

