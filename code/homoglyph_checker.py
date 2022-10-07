# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 12:04:20 2022

@author: bryan

This file contains methods to determine whether or not a spelling mistake
is homoglyphic when counting errors in OCR-ed text.
"""


import re
from homoglyph_spell_check_utils import create_homoglyph_dict

homoglyph_dict = create_homoglyph_dict(sensitivity=.2, homoglyph_fp=r'C:\Users\bryan\Documents\NBER\OCR_error_correction\code\utils\homoglyph_list.json')

def is_error_homoglyphic(ocr, gold):
    '''Strip out spaces, don't want to consider them'''
    ocr = re.sub(' ', '', ocr)
    gold = re.sub(' ', '', gold)

    if len(ocr) > 3 or len(gold) > 3:
        return 'nonhomoglyph'
    else:
        for ch_ocr in ocr:
            for ch_gold in gold:
                try:
                    if ch_gold in homoglyph_dict[ch_ocr]:
                        return 'homoglyph'
                except KeyError:
                    pass
    return 'nonhomoglyph'