# Adapted (roughly and quickly) by axwalker
# ----------------------------------------------------
# - pypacker: written by Joe Wezorek
# - license:  WTFPL
# - If you use this code and/or have suggestions, etc.,
# - email me at jwezorek@gmail.com

import os
import sys
import copy
from PIL import Image, ImageDraw
from optparse import OptionParser
from math import log, ceil


def sort_images_by_size(image_files):
    # sort by area (secondary key)
    sorted_images = sorted(
        image_files, key=lambda img_pair: img_pair.img.size[0] * img_pair.img.size[1]
    )
    # sort by max dimension (primary key)
    sorted_images = sorted(
        sorted_images,
        key=lambda img_pair: max(img_pair.img.size[0], img_pair.img.size[1]),
    )
    return sorted_images


# ----------------------------------------------------------------------


class img_pair:

    def __init__(self, name, img):
        self.name = name
        self.img = img


# ----------------------------------------------------------------------


class rectangle:

    def __init__(self, x=0, y=0, wd=0, hgt=0):
        self.x = x
        self.y = y
        self.wd = wd
        self.hgt = hgt

    def split_vert(self, y):
        top = rectangle(self.x, self.y, self.wd, y)
        bottom = rectangle(self.x, self.y + y, self.wd, self.hgt - y)
        return (top, bottom)

    def split_horz(self, x):
        left = rectangle(self.x, self.y, x, self.hgt)
        right = rectangle(self.x + x, self.y, self.wd - x, self.hgt)
        return (left, right)

    def area(self):
        return self.wd * self.hgt

    def max_side(self):
        return max(self.wd, self.hgt)

    def can_contain(self, wd, hgt):
        return self.wd >= wd and self.hgt >= hgt

    def is_congruent_with(self, wd, hgt):
        return self.wd == wd and self.hgt == hgt

    def to_string(self):
        return "<(%d, %d) - (%d, %d)>" % (self.x, self.y, self.wd, self.hgt)

    def should_split_vertically(self, wd, hgt):
        if self.wd == wd:
            return True
        elif (self.hgt == hgt):
            return False
        # TODO: come up with a better heuristic
        vert_rects = self.split_vert(hgt)
        horz_rects = self.split_horz(wd)
        return vert_rects[1].area() > horz_rects[1].area()

    def should_grow_vertically(self, wd, hgt):
        can_grow_vert = self.wd >= wd
        can_grow_horz = self.hgt >= hgt
        if not can_grow_vert and not can_grow_horz:
            raise Exception("Unable to grow!")
        if can_grow_vert and not can_grow_horz:
            return True
        if can_grow_horz and not can_grow_vert:
            return False
        return (self.hgt + hgt < self.wd + wd)


# ----------------------------------------------------------------------
class rect_node:

    def __init__(self, img_pair, rect=(), children=()):
        self.rect = rect
        if img_pair:
            self.img_name = img_pair.name
            self.img = img_pair.img
        else:
            self.img_name = ()
            self.img = ()
        self.children = children

    def clone(self):
        if self.is_leaf():
            return rect_node(img_pair(self.img_name, self.img), copy.copy(self.rect))
        else:
            return rect_node(
                img_pair(self.img_name, self.img),
                copy.copy(self.rect),
                (self.children[0].clone(), self.children[1].clone()),
            )

    def is_leaf(self):
        return not self.children

    def is_empty_leaf(self):
        return (self.is_leaf() and not self.img)

    def split_node(self, img_pair):
        if not self.is_leaf:
            raise Exception("Attempted to split non-leaf")

        (img_wd, img_hgt) = img_pair.img.size
        if not self.rect.can_contain(img_wd, img_hgt):
            raise Exception("Attempted to place an img in a node it doesn't fit")

        # if it fits exactly then we are done...
        if self.rect.is_congruent_with(img_wd, img_hgt):
            self.img_name = img_pair.name
            self.img = img_pair.img
        else:
            if self.rect.should_split_vertically(img_wd, img_hgt):
                vert_rects = self.rect.split_vert(img_hgt)
                top_child = rect_node((), vert_rects[0])
                bottom_child = rect_node((), vert_rects[1])
                self.children = (top_child, bottom_child)
            else:
                horz_rects = self.rect.split_horz(img_wd)
                left_child = rect_node((), horz_rects[0])
                right_child = rect_node((), horz_rects[1])
                self.children = (left_child, right_child)
            self.children[0].split_node(img_pair)

    def grow_node(self, img_pair):
        if self.is_empty_leaf():
            raise Exception("Attempted to grow an empty leaf")
        (img_wd, img_hgt) = img_pair.img.size
        new_child = self.clone()
        self.img = ()
        self.img_name = ()
        if self.rect.should_grow_vertically(img_wd, img_hgt):
            self.children = (
                new_child,
                rect_node(
                    (),
                    rectangle(
                        self.rect.x, self.rect.y + self.rect.hgt, self.rect.wd, img_hgt
                    ),
                ),
            )
            self.rect.hgt += img_hgt
        else:
            self.children = (
                new_child,
                rect_node(
                    (),
                    rectangle(
                        self.rect.x + self.rect.wd, self.rect.y, img_wd, self.rect.hgt
                    ),
                ),
            )
            self.rect.wd += img_wd
        self.children[1].split_node(img_pair)

    def to_string(self):
        if self.is_leaf():
            return "[ %s: %s ]" % (self.img_name, self.rect.to_string())
        else:
            return "[ %s: %s | %s %s]" % (
                self.img_name,
                self.rect.to_string(),
                self.children[0].to_string(),
                self.children[1].to_string(),
            )

    def render(self, img):
        if self.is_leaf():
            if self.img:
                img.paste(self.img, (self.rect.x, self.rect.y))
        else:
            self.children[0].render(img)
            self.children[1].render(img)


# ----------------------------------------------------------------------


def find_empty_leaf(node, img):
    (img_wd, img_hgt) = img.size
    if node.is_empty_leaf():
        return node if node.rect.can_contain(img_wd, img_hgt) else ()
    else:
        if node.is_leaf():
            return ()
        leaf = find_empty_leaf(node.children[0], img)
        if leaf:
            return leaf
        else:
            return find_empty_leaf(node.children[1], img)


def pack_images(named_images, grow_mode, max_dim=None):
    root = ()
    while named_images:
        named_image = named_images.pop()
        if not root:
            if grow_mode:
                root = rect_node(
                    (),
                    rectangle(0, 0, named_image.img.size[0], named_image.img.size[1]),
                )
            else:
                root = rect_node((), rectangle(0, 0, max_dim[0], max_dim[1]))
            root.split_node(named_image)
            continue
        leaf = find_empty_leaf(root, named_image.img)
        if leaf:
            leaf.split_node(named_image)
        else:
            if grow_mode:
                root.grow_node(named_image)
            else:
                raise Exception(
                    "Can't pack images into a %d by %d rectangle." % max_dim
                )
    return root


def flatten_nodes(node):
    if node.is_leaf():
        if node.img:
            return [node]
        else:
            return ()
    else:
        left = flatten_nodes(node.children[0])
        right = flatten_nodes(node.children[1])
        if left and not right:
            return left
        if right and not left:
            return right
        if left and right:
            return left + right
        else:
            return ()


def generate_sprite_sheet_img(packing, image_filename):
    sz = (packing.rect.wd, packing.rect.hgt)
    sprite_sheet = Image.new("RGBA", sz)
    packing.render(sprite_sheet)
    sprite_sheet.save(image_filename, "PNG")
    return sprite_sheet


def generate_sprite_sheet(packing, dest_file_prefix):
    image_filename = dest_file_prefix + ".png"
    img = generate_sprite_sheet_img(packing, image_filename)


def get_images(image_dir):
    images = []
    for file in os.listdir(image_dir):
        img = ()
        try:
            img = Image.open(image_dir + os.sep + file)
        except:
            continue
        if not images:
            images = [img_pair(file, img)]
        else:
            images.append(img_pair(file, img))
    return images


def make_collage(images, with_filename):
    images = [img_pair(i[0], i[1]) for i in images]
    sorted_images = sort_images_by_size(images)
    image_packing = pack_images(sorted_images, grow_mode=True)
    generate_sprite_sheet_img(image_packing, with_filename)
