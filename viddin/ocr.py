# Copyright 2022 by Chris Osborn <fozztexx@fozztexx.com>
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

import sys
import cv2
from openvino.runtime import Core
from pathlib import Path
import math
import numpy as np
import re
import viddin
from viddin.tessocr import TessOCR

PAST_TITLE = ["producer", "guest", "starring", "directed", "produced", "written",
              "writer", "storyboard"]

class TextResnet:
  MODEL_DIR = "~/open_model_zoo_models"
  MODEL_PRECISION = "FP32"
  MODELS = {
    "bounds": ["intel", "horizontal-text-detection-0001"],
    "recognize": ["public", "text-recognition-resnet-fc"],
  }

  def __init__(self):
    super().__init__()
    self.engine = Core()
    self.detectors = {}

    model_dir = Path(self.MODEL_DIR).expanduser()
    for model in self.MODELS:
      mp = self.MODELS[model]
      path = (model_dir / mp[0] / mp[1] / self.MODEL_PRECISION / mp[1]).with_suffix(".xml")
      loaded = self.engine.read_model(model=path, weights=path.with_suffix(".bin"))
      compiled = self.engine.compile_model(model=loaded, device_name="CPU")
      self.detectors[model] = compiled
    return

  def multiplyByRatio(self, ratio_x, ratio_y, box):
    return [max(shape * ratio_y, 10) if idx % 2 else shape * ratio_x
            for idx, shape in enumerate(box[:-1])]

  def runPreprocesingOnCrop(self, crop, net_shape):
    temp_img = cv2.resize(crop, net_shape)
    temp_img = temp_img.reshape((1,) * 2 + temp_img.shape)
    return temp_img

  def recognizeText(self, frame):
    grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    N, C, H, W = self.detectors['bounds'].input(0).shape
    resized_image = cv2.resize(frame, (W, H))
    input_image = np.expand_dims(resized_image.transpose(2, 0, 1), 0)

    output_key = self.detectors['bounds'].output("boxes")
    boxes = self.detectors['bounds']([input_image])[output_key]
    boxes = boxes[~np.all(boxes == 0, axis=1)]

    _, _, H, W = self.detectors['recognize'].input(0).shape
    (real_y, real_x), (resized_y, resized_x) = grayscale.shape[:2], resized_image.shape[:2]
    ratio_x, ratio_y = real_x / resized_x, real_y / resized_y

    letters = "~0123456789abcdefghijklmnopqrstuvwxyz"

    annotations = []
    for i, crop in enumerate(boxes):
      (x_min, y_min, x_max, y_max) = map(int, self.multiplyByRatio(ratio_x, ratio_y, crop))
      image_crop = self.runPreprocesingOnCrop(grayscale[y_min:y_max, x_min:x_max], (W, H))
      result = self.detectors['recognize']([image_crop]) \
               [self.detectors['recognize'].output(0)]
      recognition_results_test = np.squeeze(result)

      annotation = []
      for letter in recognition_results_test:
        parsed_letter = letters[letter.argmax()]

        # Returning 0 index from `argmax` signalizes an end of a string.
        if parsed_letter == letters[0]:
            break
        annotation.append(parsed_letter)
      annotations.append("".join(annotation))

    return annotations

class OCR:
  _engine = None

  def __init__(self, media, episodes, minimumWordLength=3, commonWords=None, bounds=None,
               pastTitleWords=None):
    self.video = cv2.VideoCapture(media.path)
    self.episodes = viddin.EpisodeList(episodes, "dvdID")
    if commonWords is not None:
      self.episodes.commonWords = self.episodes.commonWords | set(commonWords)
    self.minimumWordLength = minimumWordLength
    self.bounds = bounds
    if OCR._engine == None:
      OCR._engine = TextResnet()
      #OCR._engine = TessOCR()
    self.engine = OCR._engine
    self.pastTitleWords = pastTitleWords
    return

  def bisect(self, end):
    array = list(range(end))
    divisions = 2
    step = len(array) // divisions
    idx = 0
    b_array = []

    while len(b_array) < len(array):
      elem = array[idx]
      if elem is not None:
        b_array.append(elem)
        array[idx] = None
      idx += step
      if idx >= len(array):
        divisions *= 2
        step = len(array) // divisions
        idx = step

    return b_array

  def filterOrder(self, order, after, start, dur, between):
    between = sorted(between)
    order_after = order[after:]
    filtered = [x for x in order_after if between[0] <= start + x * dur <= between[1]]
    if len(filtered):
      remain = [x for x in order_after if x not in filtered]
      order[after:] = filtered + remain
      print(file=sys.stderr)
      print("Narrowing search %0.3f-%0.3f" % (between[0], between[1]), file=sys.stderr)
    return order

  def showStatus(self, offset, message=None):
    buf = "Searching %0.3f " % (offset)
    if message:
      buf += message

    width = 80
    if not viddin.Terminal().validTerminal:
      print("INVALID TERMINAL")
      exit(1)

    buf = buf[:viddin.Terminal().width - 1]
    if message:
      buf += viddin.Terminal().clearEOL
    print(buf + "\r", end="", file=sys.stderr)
    return

  def searchForTitleCard(self, position, length, within=3*60.0):
    # FIXME - get frame rate from media
    check_dur = 1 / 24
    check_max = int(math.ceil(length) / check_dur)
    check_order = self.bisect(check_max)
    skip_before = skip_after = None

    # Favor the first 5, 30, and within seconds
    if (within <= length):
      check_order = self.filterOrder(check_order, 0,
                                     position, check_dur, (position, position + within))
    if (30 <= length):
      check_order = self.filterOrder(check_order, 0,
                                     position, check_dur, (position, position + 30))
    if (5 <= length):
      check_order = self.filterOrder(check_order, 0,
                                     position, check_dur, (position, position + 5))

    idx = 0
    while idx < len(check_order):
      offset = position + check_order[idx] * check_dur
      idx += 1

      if skip_before is not None and offset < skip_before:
        continue
      if skip_after is not None and offset > skip_after:
        continue

      self.showStatus(offset)
      self.video.set(cv2.CAP_PROP_POS_MSEC, offset * 1000)
      ret, frame = self.video.read()
      if frame is None:
        continue

      if self.bounds:
        frame = frame[self.bounds[1]:self.bounds[1]+self.bounds[3],
                      self.bounds[0]:self.bounds[0]+self.bounds[2]]
                
      text = self.engine.recognizeText(frame)
      if not text:
        continue

      timecode = viddin.formatTimecode(offset)
      self.showStatus(offset, timecode + " " + str(text))
      
      l_text = " ".join(text).lower()
      did_filter = False
      if self.pastTitleWords:
        for word in self.pastTitleWords:
          if word in l_text:
            skip_after = offset
            check_order = self.filterOrder(check_order, idx,
                                           position, check_dur, (offset, offset - 15))
            did_filter = True
            break

      episode = self.episodes.findEpisodeByTitle(l_text)
      if episode is not None:
        return episode, offset, text

    return None, None, None
