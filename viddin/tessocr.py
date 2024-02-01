# Copyright 2024 by Chris Osborn <fozztexx@fozztexx.com>
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

import tesserocr
from PIL import Image
from dataclasses import dataclass

@dataclass
class OCRWord:
  text: str
  alphanum: str
  confidence: int
  bounds: list
  letters: list
  frame: int
  index: int

@dataclass
class OCRBlock:
  text: str
  words: list

class TessOCR:
  def __init__(self, lang="eng"):
    self.api = tesserocr.PyTessBaseAPI(lang="eng",
                                       path="/usr/share/tesseract-ocr/4.00/tessdata")
    self.conf_threshold = 65
    return

  def recognizeText(self, frame):
    self.api.SetImage(Image.fromarray(frame))
    self.api.Recognize()

    ocr_data = []
    
    try:
      ocr_text = self.api.AllWords()
      ocr_conf = self.api.AllWordConfidences()
      ocr_bounds = self.api.GetWords()
      ocr_bounds = [(x[1]['x'], x[1]['y'], x[1]['w'], x[1]['h']) for x in ocr_bounds]
      ocr_regions = self.api.GetComponentImages(tesserocr.RIL.SYMBOL, True)
      ocr_regions = [(x[1]['x'], x[1]['y'], x[1]['w'], x[1]['h']) for x in ocr_regions]
      ocr_lines = self.api.GetUTF8Text()
      ocr_slines = [x.split() for x in ocr_lines.split("\n")]
      #ocr_lines = self.api.GetBoxText(0)

      # print("TEXT", len(ocr_text), len("".join(ocr_text)), ocr_text)
      # print("LINES", len(ocr_lines), ocr_lines)
      # print("REGIONS", len(ocr_regions), ocr_regions)

      ocr_rebounds = []
      idx = word = 0
      box = None
      lo = ln = 0
      ocr_relines = [[]]
      for r_idx, bb in enumerate(ocr_regions):
        if box is None:
          box = list(bb)
        else:
          box[0] = min(bb[0], box[0])
          box[1] = min(bb[1], box[1])
          box[2] = max(bb[0] + bb[2], box[0] + box[2]) - box[0]
          box[3] = max(bb[1] + bb[3], box[1] + box[3]) - box[1]

        idx += 1
        if idx >= len(ocr_text[word]):
          an = ''.join(c for c in ocr_text[word].strip() if c.isalnum())
          if ocr_conf[word] >= self.conf_threshold and len(an) > 3:
            ocr_relines[-1].append(ocr_text[word])
            rb = r_idx - len(ocr_text[word]) + 1
            re = r_idx + 1
            a_word = OCRWord(ocr_text[word], an,
                             ocr_conf[word], box, ocr_regions[rb:re],
                             len(ocr_data), len(ocr_rebounds))
            ocr_rebounds.append(a_word)

          word += 1
          #print("AAAA", r_idx, len(ocr_regions), word, lo, len(ocr_slines), ln, ocr_slines)
          if ln < len(ocr_slines) and word - lo >= len(ocr_slines[ln]):
            ocr_relines.append([])
            lo += len(ocr_slines[ln])
            ln += 1

          idx_f = idx
          idx = 0
          box = None

      ocr_relines = [x for x in ocr_relines if len(x)]
      block = OCRBlock(ocr_relines, ocr_rebounds)
      # print("CONF", len(ocr_conf), ocr_conf)
      # print("BOUNDS", len(ocr_bounds), ocr_bounds)
      # print("reBOUNDS", len(ocr_rebounds), ocr_rebounds)

      if len(block.words):
        ocr_data.append(block)
    except RuntimeError:
      pass

    return [" ".join([" ".join(text) for text in block.text]) for block in ocr_data]
