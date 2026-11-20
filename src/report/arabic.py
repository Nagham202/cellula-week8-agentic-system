import re

import arabic_reshaper
# the first version of the algorithm also mirrors brackets, so ( stays ( in Arabic lines
from bidi.algorithm import get_display
from reportlab.pdfbase.pdfmetrics import stringWidth

ARABIC_LETTERS = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")


def has_arabic(text):
    return bool(ARABIC_LETTERS.search(text))


def arabic_lines(text, font, size, width):
    # 1. reshape: an Arabic letter has a different shape at the start, middle and end of a word
    words = arabic_reshaper.reshape(text).split()

    # 2. wrap: reportlab breaks lines from left to right, which is wrong for Arabic,
    #    so the lines are made here, using the real width of the words in this font
    lines, line = [], ""
    for word in words:
        longer = f"{line} {word}".strip()
        if line and stringWidth(longer, font, size) > width:
            lines.append(line)
            line = word
        else:
            line = longer
    if line:
        lines.append(line)

    # 3. order: each line is turned into the order it is drawn, right to left,
    #    while English words and numbers inside it stay left to right
    return [get_display(line, base_dir="R") for line in lines]
