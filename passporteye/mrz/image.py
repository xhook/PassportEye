'''
PassportEye::MRZ: Machine-readable zone extraction and parsing.
Image processing for MRZ extraction.

Author: Konstantin Tretyakov
License: MIT
'''
from collections import OrderedDict

from skimage import transform, io, morphology, filters, measure
import numpy as np
import tempfile, os, exifread
#opencv
import cv2
#cologram
#pip install colorgram.py
import colorgram
from ..util.pdf import extract_first_jpeg_in_pdf
from ..util.pipeline import Pipeline
from ..util.geometry import RotatedBox
from ..util.ocr import ocr
from .MRZ import MRZ
from .ELA import ELA

class Loader(object):
    """Loads `filename` to `img`."""

    __depends__ = []
    __provides__ = ['img']

    def __init__(self, filename, as_grey=True, pdf_aware=True):
        self.filename = filename
        self.as_grey = as_grey
        self.pdf_aware = pdf_aware

    def _imread(self, filename):
        """Proxy to skimage.io.imread with some fixes."""
        img = io.imread(filename, as_grey=self.as_grey)
        if img is not None and len(img.shape) != 2:
            # The PIL plugin somewhy fails to load some images
            img = io.imread(filename, as_grey=self.as_grey, plugin='matplotlib')
        return img

    def __call__(self):
        if self.pdf_aware and self.filename.lower().endswith('.pdf'):
            with open(self.filename, 'rb') as f:
                img_data = extract_first_jpeg_in_pdf(f)
            if img_data is None:
                return None
            else:
                fd, fname = tempfile.mkstemp(prefix='pythoneye_', suffix='.jpg')
                try:
                    with open(fname, 'wb') as f:
                        f.write(img_data)
                    return self._imread(fname)
                except:
                    return None
                finally:
                    os.close(fd)
                    os.remove(fname)
        else:
            return self._imread(self.filename)


class ExifReader(object):
    """ Reads EXIF """

    __depends__ = []
    __provides__ = ['exif']

    def __init__(self, filename):
        self.filename = filename

    def __call__(self):
        if self.filename.lower().endswith('.pdf'):
            return None
        else:
            try:
                with open(self.filename, 'rb') as f:
                    tags = exifread.process_file(f)
                    tags_result = [(tag, str(tags[tag])) for tag in tags.keys()]
                    return dict(tags_result)
            except:
                return None


class GreyscaleDetection(object):
    """Takes image, says greyscale or not"""
    # TODO FIGURE OUT WHY IT'S FAILING FOR GREYSCALE IMAGES. THOUGH, RETURNS CORRECTLY FOR COLORFUL IMAGES

    __depends__ = []
    __provides__ = ['is_greyscale']

    def __init__(self, filename):
        self.filename = filename

    def __call__(self):
        img = io.imread(self.filename,  plugin='matplotlib')
        if len(img.shape) == 3:
            colors = colorgram.extract(self.filename, 20)
            check = True
            for col in colors:
                if np.std(col.rgb) > 10:
                    check = False
            return check
        else:
            return True


class BlurDetection(object):
    """Detects blurry images"""

    __depends__ = []
    __provides__ = ['is_blurry']

    def __init__(self, filename):
        self.filename = filename

    def __call__(self):
        threshold = 250
        img = cv2.imread(self.filename)
        grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        fm = cv2.Laplacian(grey, cv2.CV_64F).var()
        if fm < threshold:
            return True
        return False


class Scaler(object):
    """Scales `image` down to `img_scaled` so that its width is at most 250."""

    __depends__ = ['img']
    __provides__ = ['img_small', 'scale_factor']

    def __init__(self, max_width=250):
        self.max_width = max_width

    def __call__(self, img):
        scale_factor = self.max_width/float(img.shape[1])
        if scale_factor <= 1:
            img_small = transform.rescale(img, scale_factor)
        else:
            scale_factor = 1.0
            img_small = img
        return img_small, scale_factor


class BooneTransform(object):
    """Processes `img_small` according to Hans Boone's method
    (http://www.pyimagesearch.com/2015/11/30/detecting-machine-readable-zones-in-passport-images/)
    Outputs a `img_binary` - a result of threshold_otsu(closing(sobel(black_tophat(img_small)))"""

    __depends__ = ['img_small']
    __provides__ = ['img_binary']

    def __init__(self, square_size=5):
        self.square_size = 5

    def __call__(self, img_small):
        m = morphology.square(self.square_size)
        img_th = morphology.black_tophat(img_small, m)
        img_sob = abs(filters.sobel_v(img_th))
        img_closed = morphology.closing(img_sob, m)
        threshold = filters.threshold_otsu(img_closed)
        return img_closed > threshold


class MRZBoxLocator(object):
    """Extracts putative MRZs as RotatedBox instances from the contours of `img_binary`"""

    __depends__ = ['img_binary']
    __provides__ = ['boxes']

    def __init__(self, max_boxes=4, min_points_in_contour=50, min_area=500, min_box_aspect=5, angle_tol=0.1, lineskip_tol=1.5, box_type='bb'):
        self.max_boxes = max_boxes
        self.min_points_in_contour = min_points_in_contour
        self.min_area = min_area
        self.min_box_aspect = min_box_aspect
        self.angle_tol = angle_tol
        self.lineskip_tol = lineskip_tol
        self.box_type = box_type

    def __call__(self, img_binary):
        cs = measure.find_contours(img_binary, 0.5)

        # Collect contours into RotatedBoxes
        results = []
        for c in cs:
            # Now examine the bounding box. If it is too small, we ignore the contour
            ll, ur = np.min(c, 0), np.max(c, 0)
            wh = ur - ll
            if wh[0]*wh[1] < self.min_area: continue

            # Finally, construct the rotatedbox. If its aspect ratio is too small, we ignore it
            rb = RotatedBox.from_points(c, self.box_type)
            if rb.height == 0 or rb.width/rb.height < self.min_box_aspect: continue

            # All tests fine, add to the list
            results.append(rb)

        # Next sort and leave only max_boxes largest boxes by area
        results.sort(lambda x,y: 1 if x.area < y.area else -1)
        return self._merge_boxes(results[0:self.max_boxes])

    def _are_aligned_angles(self, b1, b2):
        "Are two boxes aligned according to their angle?"
        return abs(b1 - b2) <= self.angle_tol or abs(np.pi - abs(b1 - b2)) <= self.angle_tol

    def _are_nearby_parallel_boxes(self, b1, b2):
        "Are two boxes nearby, parallel, and similar in width?"
        if not self._are_aligned_angles(b1.angle, b2.angle): return False
        # Otherwise pick the smaller angle and see whether the two boxes are close according to the "up" direction wrt that angle
        angle = min(b1.angle, b2.angle)
        return abs(np.dot(b1.center - b2.center, [-np.sin(angle), np.cos(angle)])) < self.lineskip_tol*(b1.height + b2.height) and \
               (b1.width > 0) and (b2.width > 0) and (0.5 < b1.width/b2.width < 2.0)

    def _merge_any_two_boxes(self, box_list):
        """Given a list of boxes, finds two nearby parallel ones and merges them. Returns false if none found."""
        for i in range(len(box_list)):
            for j in range(i+1,len(box_list)):
                if self._are_nearby_parallel_boxes(box_list[i], box_list[j]):
                    # Remove the two boxes from the list, add a new one
                    a, b = box_list[i], box_list[j]
                    merged_points = np.vstack([a.points, b.points])
                    merged_box =  RotatedBox.from_points(merged_points, self.box_type)
                    if merged_box.width/merged_box.height >= self.min_box_aspect:
                        box_list.remove(a)
                        box_list.remove(b)
                        box_list.append(merged_box)
                        return True
        return False

    def _merge_boxes(self, box_list):
        """Mergest nearby parallel boxes in the given list."""
        while self._merge_any_two_boxes(box_list):
            pass
        return box_list


class FindFirstValidMRZ(object):
    """Iterates over boxes found by MRZBoxLocator, passes them to BoxToMRZ, finds the first valid MRZ
    or the best-scoring MRZ"""

    __provides__ = ['box_idx', 'roi', 'text', 'mrz', 'mrz_box']
    __depends__ = ['boxes', 'img', 'img_small', 'scale_factor', '__data__']

    def __init__(self, use_original_image=True):
        self.box_to_mrz = BoxToMRZ(use_original_image)

    def __call__(self, boxes, img, img_small, scale_factor, data):
        mrzs = []
        data['__debug__mrz'] = []
        for i, b in enumerate(boxes):
            roi, text, mrz, mrz_box = self.box_to_mrz(b, img, img_small, scale_factor)
            data['__debug__mrz'].append((roi, text, mrz))
            if mrz.valid:
                return i, roi, text, mrz, mrz_box
            elif mrz.valid_score > 0:
                mrzs.append((i, roi, text, mrz, mrz_box))
        if len(mrzs) == 0:
            return None, None, None, None, None
        else:
            mrzs.sort(cmp=lambda x, y: x[3].valid_score - y[3].valid_score)
            return mrzs[-1]


class BoxToMRZ(object):
    """Extracts ROI from the image, corresponding to a box found by MRZBoxLocator, does OCR and MRZ parsing on this region."""

    __provides__ = ['roi', 'text', 'mrz', 'mrz_box']
    __depends__ = ['box', 'img', 'img_small', 'scale_factor']

    def __init__(self, use_original_image=True):
        """
        :param use_original_image: when True, the ROI is extracted from img, otherwise from img_small
        """
        self.use_original_image = use_original_image

    def __call__(self, box, img, img_small, scale_factor):
        img = img if self.use_original_image else img_small
        scale = 1.0/scale_factor if self.use_original_image else 1.0

        # If the box's angle is np.pi/2 +- 0.01, we shall round it to np.pi/2:
        # this way image extraction is fast and introduces no distortions.
        # and this may be more important than being perfectly straight
        # similar for 0 angle
        if abs(abs(box.angle) - np.pi/2) <= 0.01:
            box.angle = np.pi/2
        if abs(box.angle) <= 0.01:
            box.angle = 0.0

        roi = box.extract_from_image(img, scale)
        text = ocr(roi)

        if '>>' in text or ('>' in text and '<' not in text):
            # Most probably we need to reverse the ROI
            roi = roi[::-1,::-1]
            text = ocr(roi)

        if not '<' in text:
            # Assume this is unrecoverable and stop here (TODO: this may be premature, although it saves time on useless stuff)
            return roi, text, MRZ.from_ocr(text), box

        mrz = MRZ.from_ocr(text)
        mrz.aux['method'] = 'direct'

        # Now try improving the result via hacks
        if not mrz.valid:
            text, mrz = self._try_larger_image(roi, text, mrz)

        # Sometimes the filter used for enlargement is important!
        if not mrz.valid:
            text, mrz = self._try_larger_image(roi, text, mrz, 1)

        if not mrz.valid:
            text, mrz = self._try_black_tophat(roi, text, mrz)

        return roi, text, mrz, box

    def _try_larger_image(self, roi, cur_text, cur_mrz, filter_order=3):
        """Attempts to improve the OCR result by scaling the image. If the new mrz is better, returns it, otherwise returns
        the old mrz."""
        if roi.shape[1] <= 700:
            scale_by = int(1050.0/roi.shape[1] + 0.5)
            roi_lg = transform.rescale(roi, scale_by, order=filter_order)
            new_text = ocr(roi_lg)
            new_mrz = MRZ.from_ocr(new_text)
            new_mrz.aux['method'] = 'rescaled(%d)' % filter_order
            if new_mrz.valid_score > cur_mrz.valid_score:
                cur_mrz = new_mrz
                cur_text = new_text
        return cur_text, cur_mrz

    def _try_black_tophat(self, roi, cur_text, cur_mrz):
        roi_b = morphology.black_tophat(roi, morphology.disk(5))
        new_text = ocr(roi_b)  # There are some examples where this line basically hangs for an undetermined amount of time.
        new_mrz = MRZ.from_ocr(new_text)
        if new_mrz.valid_score > cur_mrz.valid_score:
            new_mrz.aux['method'] = 'black_tophat'
            cur_text, cur_mrz = new_text, new_mrz

        new_text, new_mrz = self._try_larger_image(roi_b, cur_text, cur_mrz)
        if new_mrz.valid_score > cur_mrz.valid_score:
            new_mrz.aux['method'] = 'black_tophat(rescaled(3))'
            cur_text, cur_mrz = new_text, new_mrz

        return cur_text, cur_mrz


class TryOtherMaxWidth(object):
    """
    If mrz was not found so far in the current pipeline,
    changes the max_width parameter of the scaler to 1000 and reruns the pipeline again.
    """

    __provides__ = ['mrz_final']
    __depends__ = ['mrz', '__pipeline__']

    def __init__(self, other_max_width=1000):
        self.other_max_width = other_max_width

    def __call__(self, mrz, __pipeline__):
        # We'll only try this if we see that img_binary.mean() is very small or img.mean() is very large (i.e. image is mostly white).
        if mrz is None and (__pipeline__['img_binary'].mean() < 0.01 or __pipeline__['img'].mean() > 0.95):
            __pipeline__.replace_component('scaler', Scaler(self.other_max_width))
            new_mrz = __pipeline__['mrz']
            new_mrz.aux['method'] = new_mrz.aux['method'] + '|max_width(%d)' % self.other_max_width
            mrz = new_mrz
        return mrz


class ResultComposer(object):
    """
    Composes results into a single map
    """

    __provides__ = ['result']
    __depends__ = ['mrz_final', 'mrz_box', 'exif', 'ela_max_diff', 'is_greyscale', 'is_blurry']

    def __init__(self):
        pass

    def __call__(self, mrz_final, mrz_box, exif, ela_max_diff, is_greyscale, is_blurry):
        # type: (MRZ, RotatedBox, dict) -> dict
        if mrz_final is None:
            return OrderedDict()
        mrz_dict = mrz_final.to_dict()
        box_poly = mrz_box.as_poly().tolist()

        result = OrderedDict()
        result['mrz'] = mrz_dict
        result['mrz']['bounding_box'] = box_poly
        result['ela'] = {}
        result['ela']['max_diff'] = ela_max_diff
        result['exif'] = exif
        result['is_greyscale'] = is_greyscale
        result['is_blurry'] = is_blurry
        return result


class MRZPipeline(Pipeline):
    """This is the "currently best-performing" pipeline for parsing MRZ from a given image file."""

    def __init__(self, filename):
        super(MRZPipeline, self).__init__()
        self.version = '1.0'  # In principle we might have different pipelines in use, so possible backward compatibility is an issue
        self.filename = filename
        self.add_component('loader', Loader(filename))
        self.add_component('ela', ELA(filename))
        self.add_component('exif_reader', ExifReader(filename))
        self.add_component('greyscale_detection', GreyscaleDetection(filename))
        self.add_component('blur_detection', BlurDetection(filename))
        self.add_component('scaler', Scaler())
        self.add_component('boone', BooneTransform())
        self.add_component('box_locator', MRZBoxLocator())
        self.add_component('mrz', FindFirstValidMRZ())
        self.add_component('other_max_width', TryOtherMaxWidth())
        self.add_component('result_composer', ResultComposer())
    @property
    def result(self):
        return self['result']


def read_mrz(filename, save_roi=False):
    """The main interface function to this module, encapsulating the recognition pipeline.
       Given an image filename, runs MRZPipeline on it, returning the parsed MRZ object.

    :param save_roi: when this is True, the .aux['roi'] field will contain the Region of Interest where the MRZ was parsed from.
    """
    p = MRZPipeline(filename)
    mrz = p.result

    if mrz is not None:
        if save_roi:
            mrz.aux['roi'] = p['roi']
    return mrz
