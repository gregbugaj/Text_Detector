import torch
from torchvision import transforms
import cv2
import numpy as np
import types
from numpy import random


def intersect(box_a, box_b):
    max_xy = np.minimum(box_a[:, 2:], box_b[2:])
    min_xy = np.maximum(box_a[:, :2], box_b[:2])
    inter = np.clip((max_xy - min_xy), a_min=0, a_max=np.inf)
    return inter[:, 0] * inter[:, 1]


def jaccard_numpy(box_a, box_b):
    """Compute the jaccard overlap of two sets of boxes.  The jaccard overlap
    is simply the intersection over union of two boxes.
    E.g.:
        A ∩ B / A ∪ B = A ∩ B / (area(A) + area(B) - A ∩ B)
    Args:
        box_a: Multiple bounding boxes, Shape: [num_boxes,4]
        box_b: Single bounding box, Shape: [4]
    Return:
        jaccard overlap: Shape: [box_a.shape[0], box_a.shape[1]]
    """
    inter = intersect(box_a, box_b)
    area_a = ((box_a[:, 2]-box_a[:, 0]) *
              (box_a[:, 3]-box_a[:, 1]))  # [A,B]
    area_b = ((box_b[2]-box_b[0]) *
              (box_b[3]-box_b[1]))  # [A,B]
    union = area_a + area_b - inter
    return inter / union  # [A,B]

def modified_jaccard_numpy(box_a, box_b):
    """Compute the jaccard overlap of two sets of boxes.  The jaccard overlap
    is simply the intersection over union of two boxes.
    E.g.:
        A ∩ B / A ∪ B = A ∩ B / (area(A) + area(B) - A ∩ B)
    Args:
        box_a: Multiple bounding boxes, Shape: [num_boxes,4]
        box_b: Single bounding box, Shape: [4]
    Return:
        jaccard overlap: Shape: [box_a.shape[0], box_a.shape[1]]
    """
    inter = intersect(box_a, box_b)
    area_a = ((box_a[:, 2]-box_a[:, 0]) *
              (box_a[:, 3]-box_a[:, 1]))  # [A,B]
    # area_b = ((box_b[2]-box_b[0]) *
    #           (box_b[3]-box_b[1]))  # [A,B]
    # union = area_a + area_b - inter
    union = area_a
    return inter / union  # [A,B]


class Compose(object):
    """Composes several augmentations together.
    Args:
        transforms (List[Transform]): list of transforms to compose.
    Example:
        >>> augmentations.Compose([
        >>>     transforms.CenterCrop(10),
        >>>     transforms.ToTensor(),
        >>> ])
    """

    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, img, boxes=None, labels=None):
        for t in self.transforms:
            img, boxes, labels = t(img, boxes, labels)
        return img, boxes, labels


class ConvertFromInts(object):
    def __call__(self, image, boxes=None, labels=None):
        return image.astype(np.float32), boxes, labels


class Normalize(object):
    def __init__(self, mean=(0.485,0.456,0.406), var=(0.229,0.224,0.225)):
        self.mean = np.array(mean, dtype=np.float32)
        self.var = np.array(var, dtype=np.float32)

    def __call__(self, image, boxes=None, labels=None):
        image = image.astype(np.float32)
        image /= 255.
        image -= self.mean
        image /= self.var
        return image, boxes, labels


class Resize(object):
    def __init__(self, size):
        self.size = size

    def __call__(self, image, boxes=None, labels=None):
        h, w, _ = image.shape
        if boxes is not None:
            new_wh = np.array([self.size / w, self.size / h], dtype=np.float32)
            boxes = boxes * np.tile(new_wh, 4)

        image = cv2.resize(image.astype(np.uint8), (self.size,
                                 self.size), interpolation=cv2.INTER_CUBIC)

        return image, boxes, labels


class RandomSaturation(object):
    def __init__(self, lower=0.5, upper=1.5):
        self.lower = lower
        self.upper = upper
        assert self.upper >= self.lower, "contrast upper must be >= lower."
        assert self.lower >= 0, "contrast lower must be non-negative."

    def __call__(self, image, boxes=None, labels=None):
        if random.randint(2):
            image[:, :, 1] *= random.uniform(self.lower, self.upper)
            image[image>255] = 255
            image[image<0] = 0
        return image, boxes, labels


class RandomHue(object):
    def __init__(self, delta=36.0):
        assert delta >= 0.0 and delta <= 360.0
        self.delta = delta

    def __call__(self, image, boxes=None, labels=None):
        if random.randint(2):
            image[:, :, 0] += random.uniform(-self.delta, self.delta)
            image[:, :, 0][image[:, :, 0] > 360.0] -= 360.0
            image[:, :, 0][image[:, :, 0] < 0.0] += 360.0
        return image, boxes, labels


class RandomLightingNoise(object):
    def __init__(self):
        self.perms = ((0, 1, 2), (0, 2, 1),
                      (1, 0, 2), (1, 2, 0),
                      (2, 0, 1), (2, 1, 0))

    def __call__(self, image, boxes=None, labels=None):
        if random.randint(2):
            swap = self.perms[random.randint(len(self.perms))]
            shuffle = SwapChannels(swap)  # shuffle channels
            image = shuffle(image)
        return image, boxes, labels


class ConvertColor(object):
    def __init__(self, current='BGR', transform='HSV'):
        self.transform = transform
        self.current = current

    def __call__(self, image, boxes=None, labels=None):
        if self.current == 'BGR' and self.transform == 'HSV':
            image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        elif self.current == 'HSV' and self.transform == 'BGR':
            image = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        else:
            raise NotImplementedError
        return image, boxes, labels


class RandomContrast(object):
    def __init__(self, lower=0.5, upper=1.5):
        self.lower = lower
        self.upper = upper
        assert self.upper >= self.lower, "contrast upper must be >= lower."
        assert self.lower >= 0, "contrast lower must be non-negative."

    # expects float image
    def __call__(self, image, boxes=None, labels=None):
        if random.randint(2):
            alpha = random.uniform(self.lower, self.upper)
            image *= alpha
            image[image>255] = 255
            image[image<0] = 0
        return image, boxes, labels


class RandomBrightness(object):
    def __init__(self, delta=16):
        assert delta >= 0.0
        assert delta <= 255.0
        self.delta = delta

    def __call__(self, image, boxes=None, labels=None):
        if random.randint(2):
            delta = random.uniform(-self.delta, self.delta)
            image += delta
            image[image>255] = 255
            image[image<0] = 0
        return image, boxes, labels


class ToCV2Image(object):
    def __call__(self, tensor, boxes=None, labels=None):
        return tensor.cpu().numpy().astype(np.float32).transpose((1, 2, 0)), boxes, labels


class ToTensor(object):
    def __call__(self, cvimage, boxes=None, labels=None):

        if boxes is None:
            return torch.from_numpy(cvimage.astype(np.float32)).permute(2, 0, 1), None, None

        return torch.from_numpy(cvimage.astype(np.float32)).permute(2, 0, 1), \
            torch.from_numpy(boxes), \
            torch.from_numpy(labels)


class RandomSampleCrop(object):
    """Crop
    Arguments:
        img (Image): the image being input during training
        boxes (Tensor): the original bounding boxes in pt form
        labels (Tensor): the class labels for each bbox
        mode (float tuple): the min and max jaccard overlaps
    Return:
        (img, boxes, classes)
            img (Image): the cropped image
            boxes (Tensor): the adjusted bounding boxes in pt form
            labels (Tensor): the class labels for each bbox
    """
    def __init__(self):
        self.sample_options = (
            # using entire original input image
            None,
            # sample a patch s.t. MIN jaccard w/ obj in .1,.3,.4,.7,.9
            #(0.1, None),
            #(0.3, None),
            #(0.5, None),
            #(0.7, None),
            (0.9, None),
            # randomly sample a patch
            # (None, None),
        )

    def __call__(self, image, boxes=None, labels=None):
        height, width, _ = image.shape
        while True:
            # randomly choose a mode
            mode = random.choice(self.sample_options)
            if mode is None:
                return image, boxes, labels

            min_iou, max_iou = mode
            if min_iou is None:
                min_iou = float('-inf')
            if max_iou is None:
                max_iou = float('inf')

            # max trails (50)
            for _ in range(50):
                current_image = image

                w = random.uniform(0.3 * width, width)
                h = random.uniform(0.3 * height, height)

                # aspect ratio constraint b/t .5 & 2
                if h / w < 0.5 or h / w > 2:
                    continue

                left = random.uniform(width - w)
                top = random.uniform(height - h)

                # convert to integer rect x1,y1,x2,y2
                rect = np.array([int(left), int(top), int(left+w), int(top+h)])

                # calculate IoU (jaccard overlap) b/t the cropped and gt boxes
                overlap = jaccard_numpy(boxes, rect)

                # is min and max overlap constraint satisfied? if not try again
                if overlap.min() < min_iou or max_iou < overlap.max():
                    continue

                # cut the crop from the image
                current_image = current_image[rect[1]:rect[3], rect[0]:rect[2],:]

                """ original SSD """
                # # keep overlap with gt box IF center in sampled patch
                # centers = (boxes[:, :2] + boxes[:, 2:]) / 2.0

                # # mask in all gt boxes that above and to the left of centers
                # m1 = (rect[0] < centers[:, 0]) * (rect[1] < centers[:, 1])

                # # mask in all gt boxes that under and to the right of centers
                # m2 = (rect[2] > centers[:, 0]) * (rect[3] > centers[:, 1])

                # # mask in that both m1 and m2 are true
                # mask = m1 * m2

                """ TextBoxes SSD """
                m1 = (rect[0] < boxes[:, 2]) * (rect[1] < boxes[:, 3])
                m2 = (rect[2] > boxes[:, 0]) * (rect[3] > boxes[:, 1])
                mask = m1 * m2
    
                # have any valid boxes? try again if not
                if not mask.any():
                    continue

                # take only matching gt boxes
                current_boxes = boxes[mask, :].copy()

                # take only matching gt labels
                current_labels = labels[mask]

                # should we use the box left and top corner or the crop's
                current_boxes[:, :2] = np.maximum(current_boxes[:, :2],
                                                  rect[:2])
                # adjust to crop (by substracting crop's left,top)
                current_boxes[:, :2] -= rect[:2]

                current_boxes[:, 2:] = np.minimum(current_boxes[:, 2:],
                                                  rect[2:])
                # adjust to crop (by substracting crop's left,top)
                current_boxes[:, 2:] -= rect[:2]

                return current_image, current_boxes, current_labels

class RandomSampleCropPoly(object):
    """Crop
    Arguments:
        img (Image): the image being input during training
        boxes (Tensor): the original bounding boxes in pt form
        labels (Tensor): the class labels for each bbox
        mode (float tuple): the min and max jaccard overlaps
    Return:
        (img, boxes, classes)
            img (Image): the cropped image
            boxes (Tensor): the adjusted bounding boxes in pt form
            labels (Tensor): the class labels for each bbox
    """
    def __init__(self):
        self.sample_options = (
            # using entire original input image
            None,
            # sample a patch s.t. MIN jaccard w/ obj in .1,.3,.4,.7,.9
            # (0.1, None),
            # (0.3, None),
            # (0.5, None),
            # (0.7, None),
            # (0.9, None),
            (1, None),
            (3, None),
            (5, None),
            (7, None),
            (9, None),
            # randomly sample a patch
            # (None, None),
        )

    def __call__(self, image, boxes=None, labels=None):
        height, width, _ = image.shape
        while True:
            # randomly choose a mode
            mode = random.choice(self.sample_options)

            boxes_rect = []
            for i in range(len(boxes)):
                boxes_rect.append([min(boxes[i,::2]), min(boxes[i,1::2]), max(boxes[i,::2]), max(boxes[i,1::2])])
            boxes_rect = np.array(boxes_rect)

            if mode is None or len(boxes_rect) == 0:
                return image, boxes, labels

            min_boxes, max_boxes = mode
            if min_boxes is None:
                min_boxes = float('-inf')
            if max_boxes is None:
                max_boxes = float('inf')

            # max trails (50)
            for _ in range(50):
                current_image = image

                w = random.uniform(0.1 * width, width)
                h = random.uniform(0.1 * height, height)

                # aspect ratio constraint b/t .5 & 2
                if h / w < 0.5 or h / w > 2:
                    continue

                left = random.uniform(width - w)
                top = random.uniform(height - h)

                # convert to integer rect x1,y1,x2,y2
                rect = np.array([int(left), int(top), int(left+w), int(top+h)])

                # calculate IoU (jaccard overlap) b/t the cropped and gt boxes
                overlap = modified_jaccard_numpy(boxes_rect, rect)
                
                if (overlap > 0.9).sum() <= min_boxes or (overlap > 0.9).sum() >= max_boxes:
                    continue

                # cut the crop from the image
                current_image = current_image[rect[1]:rect[3], rect[0]:rect[2],:]

                """ No Mask """
                current_boxes = boxes.copy()
                num_pt = int(current_boxes.shape[1] / 2)
                current_boxes[:, :2*num_pt] -= rect[:2].tolist() * num_pt

                current_labels = labels

                return current_image, current_boxes, current_labels


class Expand(object):
    def __init__(self, mean):
        self.mean = mean

    def __call__(self, image, boxes, labels):
        if random.randint(2):
            return image, boxes, labels

        height, width, depth = image.shape
        ratio = random.uniform(1, 1.25)
        left = random.uniform(0, width*ratio - width)
        top = random.uniform(0, height*ratio - height)

        expand_image = np.zeros(
            (int(height*ratio), int(width*ratio), depth),
            dtype=image.dtype)
        expand_image[:, :, :] = self.mean
        expand_image[int(top):int(top + height),
                     int(left):int(left + width)] = image
        image = expand_image

        # boxes = boxes.copy()
        # for k in range(4):
        #     boxes[:, k*2:(k+1)*2] += (int(left), int(top))

        num_pt = int(boxes.shape[1] / 2)
        boxes[:, :2*num_pt] += [int(left), int(top)] * num_pt

        return image, boxes, labels


class RandomMirror(object):
    def __call__(self, image, boxes, classes):
        _, width, _ = image.shape
        if random.randint(2):
            image = image[:, ::-1]
            boxes = boxes.copy()
            boxes[:, 0::2] = width - boxes[:, 2::-2]
        return image, boxes, classes


class SwapChannels(object):
    """Transforms a tensorized image by swapping the channels in the order
     specified in the swap tuple.
    Args:
        swaps (int triple): final order of channels
            eg: (2, 1, 0)
    """

    def __init__(self, swaps):
        self.swaps = swaps

    def __call__(self, image):
        """
        Args:
            image (Tensor): image tensor to be transformed
        Return:
            a tensor with channels swapped according to swap
        """
        # if torch.is_tensor(image):
        #     image = image.data.cpu().numpy()
        # else:
        #     image = np.array(image)
        image = image[:, :, self.swaps]
        return image

class Rotate(object):
    def __init__(self, mean):
        #self.angle_option = [0, -45, -90, 45, 90]
        self.deg = 90
        self.rotate_prob = 3     # 5 -> 0.2
        self.mean = mean

    def __call__(self, image, boxes, labels):
        height, width, _ = image.shape
        center = (width/2, height/2)
        size = (width, height)

        if random.randint(self.rotate_prob) == 0:
            #angle = random.choice(self.angle_option)
            angle = random.randint(-self.deg, self.deg)
            M = cv2.getRotationMatrix2D(center, angle, 1)
            image = cv2.warpAffine(image, M, size, borderValue=self.mean)
            for k, box in enumerate(boxes):
                for l in range(4):
                    pt = np.append(box[2*l:2*(l+1)], 1)
                    rot_pt = M.dot(pt)
                    boxes[k,2*l:2*(l+1)] = rot_pt[:2]
            
        return image, boxes, labels


class PhotometricDistort(object):
    def __init__(self):
        self.pd = [
            RandomContrast(),
            ConvertColor(transform='HSV'),
            # RandomSaturation(),
            RandomHue(),
            ConvertColor(current='HSV', transform='BGR'),
            RandomContrast()
        ]
        self.rand_brightness = RandomBrightness()
        self.rand_light_noise = RandomLightingNoise()

    def __call__(self, image, boxes, labels):
        im = image.copy()
        im, boxes, labels = self.rand_brightness(im, boxes, labels)
        if random.randint(2):
            distort = Compose(self.pd[:-1])
        else:
            distort = Compose(self.pd[1:])
        im, boxes, labels = distort(im, boxes, labels)
        # im, boxes, labels = self.rand_light_noise(im, boxes, labels)
        
        im = np.clip(im, 0., 255.)
        return im, boxes, labels


class Augmentation_traininig(object):
    def __init__(self, size, mean=(104, 117, 123)):
        self.mean = mean
        self.size = size

        self.augment = Compose([
            ConvertFromInts(),
            PhotometricDistort(),
            # Rotate(self.mean),
            RandomSampleCropPoly(),
            Resize(self.size), 
            Normalize(),
            ToTensor(),
        ])

    def __call__(self, img, boxes, labels):
        return self.augment(img, boxes, labels)

class Augmentation_inference(object):
    def __init__(self, size, mean=(104, 117, 123)):
        self.mean = mean
        self.size = size

        self.augment = Compose([
            ConvertFromInts(),
            Resize(self.size), 
            Normalize(),
            ToTensor(),
        ])

    def __call__(self, img, boxes=None, labels=None):
        return self.augment(img, boxes, labels)
