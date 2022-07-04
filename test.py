import png
import sys

import drawSvg as draw
from collections import namedtuple
from typing import Dict, List
import random

FillArea = namedtuple("FillArea", "row, start, end")


def is_fill_area(*values):
    result = sum(values) / len(values) <= 255/2
    return result


def get_pixels(image: List[List[int]], initial_row_num: int, col_num: int, block_height: int) -> List[int]:
    """
    Get pixels for a particular column and N rows (block_height rows).
    """

    pixels = []
    for row_num in range(initial_row_num, initial_row_num + block_height):
        if row_num < len(image):
            pixels.append(image[row_num][col_num])

    return pixels

def get_fill_areas_by_size(image: List[List[int]], block_height: int) -> Dict[int, List[FillArea]]:
    """
    Given an image, return all the fill areas by size.

    The key of the returned map is the size of the fill area, and the value is an array of all the
    fill areas of that size. The goal is to be able to start first with the smallest fill areas.
    """


    fill_areas_by_size = {}


    for row_num in range(len(image) // block_height):
        in_filled_section = False
        start_of_filled_area = -1
        end_of_filled_area = -1
        for col_num in range(len(image[row_num])):
            start = row_num * block_height
            fill_area = is_fill_area(*get_pixels(image, start, col_num, block_height))
            if not in_filled_section and fill_area:
                start_of_filled_area = col_num
                in_filled_section = True
            elif in_filled_section and not fill_area:
                end_of_filled_area = col_num - 1
                fill_area = FillArea(row_num, start_of_filled_area, end_of_filled_area)
                fill_area_size = fill_area.end - fill_area.start
                fill_areas = fill_areas_by_size.get(fill_area_size, [])
                fill_areas.append(fill_area)
                fill_areas_by_size[fill_area_size] = fill_areas

                start_of_filled_area = -1
                end_of_filled_area = -1
                in_filled_section = False

    # TODO: If row ends in fill area, that section won't be added to the map. However,
    # this is not the case with the current logo.

    return fill_areas_by_size



def get_names_from_file(filename: str) -> List[str]:
    file = open(filename, 'r')
    names = file.read().splitlines()
    return names

def get_names_by_length(names_list: List[str]) -> Dict[int, List[str]]:
    """
    Get a map of length -> names.
    """

    names_by_length = {}
    for name in names_list:
        names = names_by_length.get(len(name), [])
        names.append(name)
        # There's no need to shuffle every time we add an element to the array, we can
        # do it one time at the end. Also, it doesn't change performance, so it's easier
        # here.
        random.shuffle(names)
        names_by_length[len(name)] = names
    return names_by_length


def get_max_chars_for_row(length: int, ideal_chars_per_pixel: float) -> int:
    return int(length // ideal_chars_per_pixel)

def pop_name_of_size(names_by_length: Dict[int, List[str]], length: int) -> str:
    names = names_by_length.get(length, [])
    if len(names) == 0:
        return ""

    name = names.pop()
    if len(names) == 0:
        names_by_length.pop(length)

    return name


def get_next_best_name_match(names_by_length: Dict[int, List[str]], row_size: int) -> str:
    if len(names_by_length) == 0:
        return ""
    min_size = sorted(names_by_length)[0]
    max_size = sorted(names_by_length)[len(names_by_length) - 1]

    if row_size < min_size:
        return ""

    if row_size >= max_size:
        return pop_name_of_size(names_by_length, max_size)

    # let's try first with exact match
    name = pop_name_of_size(names_by_length, row_size)
    # otherwise, let's just go with the smallest name
    if len(name) == 0:
        return pop_name_of_size(names_by_length, min_size)

    return name


def get_text_for_row(names_by_length: Dict[int, List[str]], row_size: int) -> str:

    result = []
    keep_getting_names = True
    while keep_getting_names:
        next_name = get_next_best_name_match(names_by_length, row_size)
        if len(next_name) == 0:
            keep_getting_names = False
        else:
            result.append(next_name)
            row_size -= len(next_name)

    return " · ".join(result)


# Here we are assuming the logo is grayscale, i.e. 8 bits per pixel (instead of 4: RGBA).
f = png.Reader(filename="logo_gs.png")

h, w, r, i = f.read()

print(f"H: {h}, W: {w}, i: {i}")
image = list(r)

block_height = 2
#ideal_chars_per_pixel = 1.83
# Magic number that relates block size with name length
ideal_chars_per_pixel = 1.47
# Another magic number, so we don't stretch names too much. Specially needed for the last line.
stretch_factor = 0.8

d = draw.Drawing(w, h,  displayInline=False)

names_by_length = get_names_by_length(get_names_from_file("final_employees_processed.txt"))
fill_areas_by_size = get_fill_areas_by_size(image, block_height)

personio_main_color = '#000000'
for area_size, fill_areas in sorted(fill_areas_by_size.items()):
    for fill_area in fill_areas:
        if fill_area.row % 2 == 0:
            # skip every other row, otherwise rows are too close together
            continue
        x = fill_area.start
        y = h - fill_area.row*block_height
        w = fill_area.end - fill_area.start
        r = draw.Rectangle(x, y, w, block_height, fill='#1248ff11')
        # Uncomment the next line to see the actual blocks
        #d.append(r)
        text = get_text_for_row(names_by_length, get_max_chars_for_row(fill_area.end - fill_area.start, ideal_chars_per_pixel))
        if len(text) > 0:
            if len(text) < w*(1 - stretch_factor):
                w = len(text)*ideal_chars_per_pixel
            d.append(draw.Text(text, 3, x, y, fill=personio_main_color, font_family="Open Sans",textLength=w))


# Just to make sure that we've used all the names
for l, names in sorted(names_by_length.items()):
    print(f"{l}: {len(names)}")


d.setPixelScale(5)
d.saveSvg('personio.svg')
