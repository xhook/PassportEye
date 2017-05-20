#!/usr/bin/env python

import os
import random
import string

from PIL import Image, ImageChops


class ELA(object):
    __depends__ = []
    __provides__ = ['ela_max_diff', 'histogram']

    def __init__(self, filename, quality=95):
        self.filename = filename
        self.quality = quality

    def random_string(self, length):
        return ''.join(random.choice(string.lowercase) for i in range(length))

    def compute_ela(self, quality, filename):
        resaved = '/tmp/' + self.random_string(20) + '.jpg'
        im = Image.open(filename)
        im.save(resaved, 'JPEG', quality=quality)
        resaved_im = Image.open(resaved)
        ela_im = ImageChops.difference(im, resaved_im)
        os.remove(resaved)
        return ela_im

    def compute_max_diff(self, ela):
        extrema = ela.getextrema()
        return max([ex[1] for ex in extrema])

    def compute_histogram(self, img):
        return img.histogram()

    def __call__(self):
        try:
            ela = self.compute_ela(self.quality, self.filename)
        except:
            # log.info("    Exception occurred while calculating ELA for file %s... ignoring" % filename)
            return None

        histogram = self.compute_histogram(ela)
        if len(histogram) != 3 * 256:
            # print("    Not RGB image %s... ignoring" % filename)
            return None

        max_diff = self.compute_max_diff(ela)

        return max_diff, histogram
