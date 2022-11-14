from pathlib import Path
from openvino.runtime import Core
import cv2
import numpy as np

class OCROpenVINO:
  MODEL_DIR = "~/open_model_zoo_models"
  MODEL_PRECISION = "FP16"
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

class OCRTesser:
  def recognizeText(frame):
    with tesserocr.PyTessBaseAPI(lang=lang) as api:
      img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      img = (255 - img)
      im_pil = Image.fromarray(img)

      api.SetImage(im_pil)
      api.Recognize()
      try:
        ocr_text = api.AllWords()
        ocr_conf = api.AllWordConfidences()
        ocr_bounds = api.GetWords()
        ocr_bounds = [(x[1]['x'], x[1]['y'], x[1]['w'], x[1]['h']) for x in ocr_bounds]
        ocr_regions = api.GetComponentImages(tesserocr.RIL.SYMBOL, True)
        ocr_regions = [(x[1]['x'], x[1]['y'], x[1]['w'], x[1]['h']) for x in ocr_regions]
        ocr_lines = api.GetUTF8Text()
        ocr_slines = [x.split() for x in ocr_lines.split("\n")]

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
            if ocr_conf[word] >= conf_threshold and len(an) > 3:
              ocr_relines[-1].append(ocr_text[word])
              rb = r_idx - len(ocr_text[word]) + 1
              re = r_idx + 1
              a_word = OCRWord(ocr_text[word], an,
                               ocr_conf[word], box, ocr_regions[rb:re],
                               len(ocr_data), len(ocr_rebounds))
              ocr_rebounds.append(a_word)

            word += 1
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
    return

  def merge_text(blocks):
    if len(blocks) == 0:
      return blocks
    #print()
    #print()
    s_blocks = group_blocks(blocks)
    #print(s_blocks)

    m_text = []

    for group in s_blocks:
      ptxt = group[0].alphanum
      pbb = group[0].bounds
      for word in group[1:]:
        bb = word.bounds
        ri = rect_intersection(pbb, bb)
        ht_pct = 0
        #print("comparing", ptxt, word.alphunum)

        match = False

        if ri:
          ht_pct = ri[3] / pbb[3]
          wd_pct = ri[2] / pbb[2]

        #print("height percent", ht_pct, ri, pbb, bb)
        if ht_pct > 0.50:
          left = min(pbb[0], bb[0])
          right = max(pbb[0] + pbb[2], bb[0] + bb[2])
          p_dist = (pbb[0] - left) / (right - left)
          b_dist = (bb[0] - left) / (right - left)
          p_cpp = len(ptxt) / pbb[2]
          b_cpp = len(word.alphanum) / bb[2]
          p_offset = int(p_dist * p_cpp)
          b_offset = int(b_dist * b_cpp)
          #print(p_dist, p_cpp, p_offset, ptxt)
          #print(b_dist, b_cpp, b_offset, word.alphanum)
          lpos = p_offset
          lstr = ptxt
          rpos = b_offset
          rstr = word.alphanum
          if b_offset < b_offset:
            lpos, rpos = rpos, lpos
            lstr, rstr = rstr, lstr
          #print(lstr, rstr)
          for idx in range(rpos - 2, rpos + 2):
            if idx < 0:
              continue
            if idx > len(lstr):
              break
            clen = min(len(rstr), len(lstr) - idx)
            lolap = lstr[idx:idx+clen]
            rolap = rstr[0:clen]
            #print("partial", lolap, rolap)
            if lolap == rolap:
              nstr = lstr[:idx] + rstr + lstr[idx+len(rstr):]
              ptxt = nstr
              top = min(pbb[1], bb[1])
              bot = max(pbb[1] + pbb[3], bb[1] + bb[3])
              pbb = (left, top, right - left, bot - top)
              match = True
              #print("MATCH", nstr, pbb)
              break

        if not match:
          # Not enough overlap
          m_text.append([ptxt, 100, pbb])
          pbb = bb
          ptxt = word.alphanum

      m_text.append([ptxt, 100, pbb])

    return m_text


