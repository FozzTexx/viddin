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
import stat
import subprocess
import json
import re
import tempfile
import xmltodict
import cv2
import ast
from viddin.dvdlang import dvdLangISO
import viddin

def _isDVD(path):
  if not os.path.exists(path):
    return False
  mode = os.stat(path).st_mode
  if stat.S_ISBLK(mode) or stat.S_ISDIR(mode):
    return True
  _, ext = os.path.splitext(path)
  if ext.lower() == ".iso":
    return True
  return False

class Media:
  def __new__(cls, path, titleNumber=None):
    if cls == Media:
      if _isDVD(path):
        return DVDTitle(path, titleNumber)
      _, ext = os.path.splitext(path)
      if ext == ".mkv":
        return MKVContainer(path)
      return VideoFile(path)
    return super().__new__(cls)

  def __init__(self, path, titleNumber=None):
    self.path = path
    self._chapters = None
    return

  def getTitleInfo(self, debugFlag=False):
    track = TitleInfo([], None)
    track.length = self.length
    return track

  def startEndForChapters(self, chapters, debugFlag=False):
    if '-' in chapters:
      chaps = chapters.split("-")
    else:
      chaps = [chapters, chapters]
    chaptimes = list(self.chapters)
    chaptimes.append(viddin.Chapter(self.getTitleInfo(debugFlag=debugFlag).length, "end"))
    start = chaptimes[int(chaps[0]) - 1]
    end = chaptimes[int(chaps[1])]
    return start.position, end.position

  def writeChapters(self):
    if self._chapters is None:
      return

    vlen = self.length
    if vlen is not None:
      if abs(vlen - self._chapters[-1].position) > 1:
        self._chapters = self._chapters.copy()
        self._chapters.append(vlen)
      cfile, cfname = tempfile.mkstemp()
      os.write(cfile, bytes(";FFMETADATA1\n", 'UTF-8'))
      for idx in range(len(self._chapters) - 1):
        if isinstance(self._chapters[idx], (int, float)):
          pos = self._chapters[idx]
          npos = self._chapters[idx+1]
          name = "Chapter %i" % (idx + 1)
        else:
          pos = self._chapters[idx].position
          if isinstance(self._chapters[idx+1], (int, float)):
            npos = self._chapters[idx+1]
          else:
            npos = self._chapters[idx+1].position
          name = self._chapters[idx].name

        os.write(cfile, bytes("[CHAPTER]\n", 'UTF-8'))
        os.write(cfile, bytes("TIMEBASE=1/1000\n", 'UTF-8'))
        os.write(cfile, bytes("START=%i\n" % (int(pos * 1000)), 'UTF-8'))
        os.write(cfile, bytes("END=%i\n" % (int(npos * 1000)), 'UTF-8'))
        os.write(cfile, bytes("title=%s\n" % (name), 'UTF-8'))
      os.close(cfile)

      dpath = os.path.dirname(self.path)
      _, ext = os.path.splitext(self.path)
      tf = tempfile.NamedTemporaryFile(suffix=ext, dir=dpath, delete=False)
      cmd = ["ffmpeg", "-y", "-i", self.path,
             "-i", cfname, "-map_metadata", "1", "-map_chapters", "1",
             "-movflags", "disable_chpl",
             "-codec",  "copy", "-map", "0", tf.name]
      stat = viddin.runCommand(cmd)
      if stat == 0:
        st = os.stat(self.path)
        os.rename(tf.name, self.path)
        os.chown(self.path, st.st_uid, st.st_gid)
        os.chmod(self.path, st.st_mode)
      else:
        os.remove(tf.name)
      os.remove(cfname)
    return

  def addChapters(self, chapters, normalizeFlag=True):
    # chapters can be a list of any combination of numbers or
    # Chapter class. If normalizeFlag is false then don't delete
    # chapters that are close to existing chapters or make sure
    # there's a chapter at the very beginning.

    if self._chapters is None:
      self._chapters = self._loadChapters()

    didEdit = False
    added = []
    for chap in chapters:
      if isinstance(chap, viddin.Chapter):
        added.append(chap)
      else:
        added.append(viddin.Chapter(chap, None))
    if len(added):
      self._chapters.extend(added)
      self._chapters.sort(key=lambda x: x.position)
      didEdit = True

    for idx, chap in enumerate(self._chapters):
      if chap.name is None:
        self._chapters[idx] = viddin.Chapter(chap.position, "Chapter %i" % (idx + 1))

    if normalizeFlag:
      didEdit = self.normalizeChapters(prefer=added) or didEdit

    return didEdit

  def chapterWithID(self, chapID):
    if self._chapters is None:
      self._chapters = self._loadChapters()

    chap = chap_idx = None
    if isinstance(chapID, str):
      if re.match("^-?[0-9]+$", chapID):
        chapID = int(chapID)
      elif re.search("[:,.]", chapID):
        chapID = float(viddin.decodeTimecode(chapID))

    if isinstance(chapID, str):
      for idx, c in enumerate(self._chapters):
        if c.name == chapID:
          chap_idx = idx
          break
    elif isinstance(chapID, int):
      chap_idx = chapID
    else:
      if isinstance(chapID, viddin.Chapter):
        chapID = chapID.position
      for idx, c in enumerate(self._chapters):
        if abs(c.position - chapID) < 2:
          chap_idx = idx
          break

    if chap_idx is not None and -len(self.chapters) <= chap_idx < len(self._chapters):
      chap = self._chapters[chap_idx]
    else:
      chap_idx = None
    return chap_idx, chap

  def deleteChapters(self, chapters):
    # chapters can be a list of any combination of ints, floats,
    # strings, or Chapter class. ints are treated as index, floats
    # are a position, strings will look for a matching chapter name.

    if self._chapters is None:
      self._chapters = self._loadChapters()
    if len(self._chapters) == 0:
      return

    didEdit = False
    for chap in chapters:
      chap_idx, _ = self.chapterWithID(chap)
      if chap_idx is not None:
        del self._chapters[chap_idx]
        didEdit = True
    return didEdit

  def setChapters(self, chapters):
    self._chapters = []
    self.addChapters(chapters)
    return

  def normalizeChapters(self, prefer=None):
    if self._chapters is None:
      self._chapters = self._loadChapters()

    didEdit = False
    if len(self._chapters) > 0 and self._chapters[0].position < 2:
      if self._chapters[0].position > 0:
        self._chapters[0] = viddin.Chapter(0, self._chapters[0].name)
        didEdit = True
    else:
      self._chapters.insert(0, viddin.Chapter(0, "Chapter 1"))
      didEdit = True

    for idx in range(len(self._chapters) - 2, -1, -1):
      chap = self._chapters[idx]
      nchap = self._chapters[idx+1]
      if abs(chap.position - nchap.position) < 1:
        if prefer is None or chap not in prefer:
          del self._chapters[idx]
        else:
          del self._chapters[idx+1]
        didEdit = True

    dedup = set([int(x.position * 1000) for x in self._chapters])
    if len(dedup) != len(self._chapters):
      cleaned = []
      for chp in self._chapters:
        pos = int(chp.position * 1000)
        if pos in dedup:
          cleaned.append(chp)
          dedup.remove(pos)
      self._chapters = cleaned
      didEdit = True

    for idx, chap in enumerate(self._chapters):
      if re.match("Chapter [0-9]+", chap.name):
        name = "Chapter %i" % (idx + 1)
        if name != chap.name:
          self._chapters[idx] = viddin.Chapter(chap.position, name)
          didEdit = True
    return didEdit

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
            tnum = idx
            break
      trk['number'] = tnum
    return parsed

  def writeTrack(self, source, trackNum, dest, debugFlag=False):
    path, ext = os.path.splitext(dest)

    # FIXME - change extension based on track type/encoding
    trk_ext = "sub"
    trk_path = "%s_%i.%s" % (path, trackNum, trk_ext)

    sub_track = Media(source)
    tinfo = sub_track.getTitleInfo()
    subs = tinfo.subtitles
    for trk in subs:
      if trk['type'] == "subtitles":
        trackNum = trk['id']
        break
    cmd = ["mkvextract", "tracks", source,
           "%i:%s" % (trackNum, trk_path)]
    if debugFlag:
      print(viddin.listToShell(cmd))
    err = viddin.runCommand(cmd)
    if err:
      print("Failed to extract")
      exit(1)
    if source != self.path:
      os.remove(source)

    sub_path = trk_path
    idx_path, ext = os.path.splitext(trk_path)
    idx_path += ".idx"
    if os.path.exists(idx_path):
      trk_path = [idx_path, trk_path]

    subs = TrackSpec(trk_path, None)
    if os.path.getsize(sub_path) == 0:
      subs.remove()
      subs = None

    return subs

  @property
  def chapters(self):
    if self._chapters is None:
      self._chapters = self._loadChapters()
    return tuple(self._chapters)

  @property
  def isDVD(self):
    return isinstance(self, DVDTitle)

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

  @property
  def subtitlePrimary(self):
    if isinstance(self.path, list):
      for p in self.path:
        _, ext = os.path.splitext(p)
        if ext == ".idx":
          return p
      return self.path[0]
    return self.path

class TitleInfo:
  def __init__(self, info, infoType):
    if infoType == "dvd":
      self.length = info['length']
      self.chapters = [viddin.Chapter(0, "Chapter 1")]
      for idx in range(len(info['chapter'])):
        chap = info['chapter'][idx]
        pos = self.chapters[-1].position
        pos += chap['length']
        self.chapters.append(viddin.Chapter(pos, "Chapter " + str(idx + 1)))
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

class DVDTitle(Media):
  def __init__(self, path, titleNumber=None):
    super().__init__(path)
    self.titleNumber = titleNumber
    return

  def getDVDInfo(self, debugFlag=False):
    cmd = ["lsdvd", "-asc", "-Oy", self.path]
    if debugFlag:
      print(viddin.listToShell(cmd))
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
      return None

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

  def getTitleInfo(self, debugFlag=False):
    dvdInfo = self.getDVDInfo(debugFlag=debugFlag)
    if dvdInfo is not None:
      return TitleInfo(dvdInfo['track'][self.titleNumber - 1], "dvd")
    print("Failed to get title info", self.titleNumber)
    return None

  def extractTrack(self, dest, trackNum, start, end, lang, debugFlag=False):
    # FIXME - what about audio tracks?
    source = self.extractDVDSubtitle(dest, trackNum, start, end, lang, debugFlag)
    sub_track = Media(source)
    tinfo = sub_track.getTitleInfo()
    subs = tinfo.subtitles
    trackNum = subs[0]['rv_track_id']

    return self.writeTrack(source, trackNum, dest)

  def extractDVDSubtitle(self, dest, trackNum, start, end, lang, debugFlag=False):
    path, ext = os.path.splitext(dest)
    ts_path = path + ".mkv"
    source = viddin.uniqueFile(ts_path)
    # FIXME - look at trackNum and figure out if it needs subtitle
    #         flags or audio flags or something else
    cmd = ["HandBrakeCLI", "-w", "1",
           "-i", self.path,
           "--title", str(self.titleNumber),
           "-o", source]

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
      print(viddin.listToShell(cmd))
    err = viddin.runCommand(cmd)

    if not os.path.exists(source):
      print("Failed to extract track")
      exit(1)
    return source

  def _loadChapters(self, debugFlag=False):
    chapters = []
    dvdInfo = self.getDVDInfo(debugFlag=debugFlag)
    chaps = dvdInfo['track'][self.titleNumber - 1]['chapter']
    chapters.append(viddin.Chapter(0, None))
    offset = 0
    for c in chaps:
      offset += c['length']
      chapters.append(viddin.Chapter(offset, None))
    return chapters

class VideoFile(Media):
  def loadSplits(self, withSilence=True):
    base, _ = os.path.splitext(self.path)
    viddin.findBlack(self.path)
    black = viddin.loadSplits(base + ".blk")
    if not withSilence:
      splits = black
    else:
      viddin.findSilence(self.path)
      silence = viddin.loadSplits(base + ".sil")
      splits = []
      for row in black:
        match = viddin.bestSilence(row, silence)
        if match:
          splits.append((match[1] - match[0]) / 2 + match[0])
        else:
          splits.append(0 - ((row[1] - row[0]) / 2 + row[0]))
    return splits

  def _loadChapters(self, debugFlag=False):
    chapters = []
    cmd = ["ffprobe", "-i", self.path, "-print_format", "json", "-show_chapters"]
    if debugFlag:
      print(viddin.listToShell(cmd))
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

  @property
  def length(self):
    if not hasattr(self, '_length'):
      cmd = ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             self.path]
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL)
      jstr = process.stdout.read()
      process.stdout.close()
      try:
        tlen = float(jstr)
      except ValueError:
        tlen = 0
      self._length = tlen
    return self._length

  @property
  def resolution(self):
    if not hasattr(self, '_resolution'):
      vid = cv2.VideoCapture(self.path)
      height = vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
      width = vid.get(cv2.CAP_PROP_FRAME_WIDTH)
      self._resolution = (width, height)
    return self._resolution

  @property
  def aspect(self):
    res = self.resolution
    return res[0] / res[1]

  @property
  def framesPerSecond(self):
    if not hasattr(self, '_fps'):
      vid = cv2.VideoCapture(self.path)
      self._fps = vid.get(cv2.CAP_PROP_FPS)
    return self._fps

class MKVContainer(VideoFile):
  @staticmethod
  def trackWithUid(uid, tracks):
    for track in tracks:
      if 'uid' in track and uid == track['uid']:
        return track
    return None

  def getTitleInfo(self, debugFlag=False):
    cmd = ["mkvmerge", "-i", "-F", "json", self.path]
    if debugFlag:
      print(viddin.listToShell(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    jstr = process.stdout.read()
    process.stdout.close()
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

    cmd = ["mkvextract", "tags", self.path]
    if debugFlag:
      print(viddin.listToShell(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    xstr = process.stdout.read()
    process.stdout.close()
    xstr = xstr.decode("UTF-8").strip()
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
          tt = self.trackWithUid(track['TrackUID'], tracks)
          if tt:
            tt.update(track)

    info = TitleInfo(tracks, None)
    info.chapters = self.chapters

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
      tlen = self.length
    info.length = tlen
    return info

  def writeChapters(self):
    if self._chapters is None:
      return

    cfile, cfname = tempfile.mkstemp()
    for idx in range(len(self._chapters)):
      if isinstance(self._chapters[idx], (int, float)):
        pos = self._chapters[idx]
        name = "Chapter %i" % (idx + 1)
      else:
        pos = self._chapters[idx].position
        name = self._chapters[idx].name
      os.write(cfile, bytes("CHAPTER%02i=%s\n" % (idx + 1, viddin.formatChapter(pos)),
                            'UTF-8'))
      os.write(cfile, bytes("CHAPTER%02iNAME=%s\n" % (idx + 1, name), 'UTF-8'))
    os.close(cfile)

    cmd = ["mkvpropedit", "-c", cfname, self.path]
    subprocess.call(cmd)
    os.remove(cfname)

  def extractTrack(self, dest, trackNum, start, end, lang, debugFlag=False):
    # If start/end were specified, the original file has to be
    # split just to split the subs, otherwise the subs will be
    # misaligned.

    source = self.path
    if start is not None or end is not None:
      ts_path = path + ".mkv"
      source = viddin.uniqueFile(ts_path)

      if start is None:
        start = 0
      start = viddin.formatTimecode(start)
      if ':' not in start:
        start = "00:" + start
      if end is None:
        end = ""
      else:
        end = viddin.formatTimecode(end)
        if ':' not in end:
          end = "00:" + end
      cmd = ["mkvmerge", "--split", "parts:%s-%s" % (start, end),
             "-o", source, self.path]
      if debugFlag:
        print(viddin.listToShell(cmd))
      viddin.runCommand(cmd)

    return self.writeTrack(source, trackNum, dest)

  @property
  def tracks(self):
    if not hasattr(self, '_tracks'):
      self._tracks = self.getTitleInfo().tracks
    return self._tracks
