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
import pty
from collections import namedtuple
import shlex
import curses
import subprocess
import datetime
import re
import magic
# import json
# import xmltodict
# import sys
# import tvdb_api
# import operator
# import math
# import ast
# import tempfile
# import csv
# import stat
# import io
# from dvdlang import dvdLangISO

Chapter = namedtuple("Chapter", ["position", "name"])

def findBlack(path):
  video, ext = os.path.splitext(path)
  video += ".blk"
  if not os.path.exists(video):
    print("Finding black")
    cmd = ["find-black", "--duration", "0.05", path, video]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
  return

def findSilence(path):
  video, ext = os.path.splitext(path)
  video += ".sil"
  if not os.path.exists(video):
    print("Finding silence")
    cmd = ["find-silence", "--threshold", "40", "--duration", "0.01", path, video]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
  return

def findCuts(filename):
  video, ext = os.path.splitext(filename)
  video += ".cut"
  if not os.path.exists(video):
    print("Finding cuts")
    cmd = ["find-cuts", "--threshold", "0.40", filename, video]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
  return

def loadSplits(filename):
  splits = []
  with open(filename) as f:
    for line in f:
      info = line.split()
      if len(info) >= 3:
        begin = float(info[1])
        end = float(info[2])
      elif len(info) == 2:
        begin = float(info[0])
        end = float(info[1])
      else:
        begin = end = float(info[0])
      center = begin + (end - begin) / 2
      splits.append([center, begin, end])
  return splits

def splitNearest(splits, position, margin=2, matchNeg=False):
  bdiff = -1
  boffset = None
  for row in splits:
    if row[0] >= 0 or matchNeg:
      diff = abs(position - abs(row[0]))
      if not boffset or diff < bdiff:
        bdiff = diff
        boffset = row
  if boffset and bdiff < margin:
    return boffset
  return None

def bestSilence(best, silence):
  bestsil = None
  for row in silence:
    begin = max(best[1], row[1])
    end = min(best[2], row[2])
    if begin <= end:
      overlap = end - begin
      center = begin + (end - begin) / 2
      if not bestsil or overlap > bestsil[0]:
        bestsil = [overlap, center, begin, end]

  if bestsil:
    return [bestsil[2], bestsil[3]]

  return None

def formatTimecode(tc):
  ft = str(datetime.timedelta(seconds = tc))
  m = re.match(r'^[0:]+', ft)
  if m:
    idx = m.span()[1]
    if idx < len(ft) and ft[idx] == '.':
      idx -= 1
    ft = ft[idx:]
  dp = ft.rfind(".")
  if dp >= 0 and dp < len(ft) - 4:
    ft = ft[:dp+4]
  if not ft:
    ft = "0"
  return ft

def formatChapter(seconds):
  hours = int(seconds / 3600)
  minutes = int((seconds / 60) % 60)
  return "%02i:%02i:%06.3f" % (hours, minutes, seconds - hours * 3600 - minutes * 60)

def decodeTimecode(tc):
  tc = tc.replace(',', '.')
  fraction = 0.0
  if re.match(".*[.][0-9]+$", tc):
    parts = re.split("[.]", tc)
    fraction = float("."+parts[1])
    tc = parts[0]

  seconds = sum(int(x) * 60 ** i for i,x in enumerate(reversed(tc.split(":"))))
  seconds += fraction
  return seconds

def listToShell(cmd):
  return " ".join([shlex.quote(x) for x in cmd])

def runCommand(cmd, debugFlag=False, stderr=None):
  do_shell = True
  if isinstance(cmd, (list, tuple)):
    do_shell = False

  if debugFlag or not Terminal().validTerminal:
    err = subprocess.call(cmd, stderr=stderr)
  else:
    pos = 0
    err = None
    master, slave = pty.openpty()
    if stderr is None:
      stderr = slave
    
    with subprocess.Popen(cmd, shell=do_shell, stdin=slave, stdout=slave, stderr=stderr,
                         close_fds=True) as p:
      m = os.fdopen(master, "rb")
      os.close(slave)
      width = Terminal().width

      try:
        while True:
          c = ord(m.read(1))
          if c > 127:
            continue
          if c == 27:
            c = ord(m.read(1))
            if c == ord('['):
              c = ord(m.read(1))
              if c == ord('K'):
                continue
          if c == 10:
            c = 13
          if (c == 13 and pos > 0) or width == 0 or pos < width - 2:
            if pos == 0:
              sys.stdout.write(Terminal().clearEOL)
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

def videosInDirectory(dir_path):
  files = os.listdir(dir_path)
  videos = []
  for f in files:
    path = os.path.join(dir_path, f)
    if os.path.isfile(path):
      mtype = magic.from_file(path, mime=True)
      if mtype.startswith("video/"):
        videos.append(path)

  videos.sort()
  return videos

class Terminal:
  _self = None

  def __new__(cls):
    if cls._self is None:
      cls._self = super().__new__(cls)
    return cls._self

  def __init__(self):
    self.validTerminal = False
    self.clearEOL = ""
    try:
      curses.setupterm()
      self.validTerminal = True
      self.clearEOL = curses.tigetstr("el")
      if self.clearEOL:
        self.clearEOL = self.clearEOL.decode()
      else:
        self.clearEOL = ""
    except curses.error:
      pass

    try:
      self.width = os.get_terminal_size().columns
    except OSError:
      self.width = 80
    return

def isint(s):
  try:
    int(s)
    return True
  except ValueError:
    return False

# This class is mostly just used to put all the functions in their own namespace
class viddin:
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
  def getDVDInfo(path, debugFlag=False):
    cmd = ["lsdvd", "-asc", "-Oy", path]
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

  @staticmethod
  def getLength(filename, title=None, chapters=None, debugFlag=False):
    cmd = ["ffprobe", "-v", "error",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1",
           filename]
    if debugFlag:
      print(viddin.listToShell(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    jstr = process.stdout.read()
    process.stdout.close()
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
    cmd = ["ffprobe", "-v", "error",
           "-select_streams", "v:0",
           "-show_entries", "stream=width,height",
           "-of", "csv=s=x:p=0",
           filename]
    if debugFlag:
      print(viddin.listToShell(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    res = process.stdout.read()
    process.stdout.close()
    res = res.decode("UTF-8").split('x')
    return (int(res[0]), int(res[1]))

  @staticmethod
  def getFrameRate(filename, debugFlag=False):
    cmd = ["ffprobe", "-v", "error",
           "-select_streams", "v:0",
           "-show_entries", "stream=r_frame_rate",
           "-of", "default=noprint_wrappers=1:nokey=1",
           filename]
    if debugFlag:
      print(viddin.listToShell(cmd))
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    fps = process.stdout.read()
    process.stdout.close()
    fps = fps.decode("UTF-8").strip()
    if '/' in fps:
      rates = fps.split('/')
      fps = float(rates[0]) / float(rates[1])
    else:
      fps = float(fps)
    return fps

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
      upath = dest + "_" + str(counter) + extension
    return upath
