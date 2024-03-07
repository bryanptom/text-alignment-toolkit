# -*- coding: utf-8 -*-
"""
Created on Wed Jul 13 13:21:56 2022

@author: bryan

This file contains the main method (and some helpers) to read in jsons with the
same text transcribed by OCR and by human transcribers (referred to as "gold"),
apply various post processing methods to the OCR-ed text, and then compare the two,
identifiying, classifying, and counting errors in the OCR-ed text.
"""

import os, sys
import json
import re
import numpy as np
from collections import Counter


sys.path.append(os.path.dirname(__file__))
from align import align_texts, check_for_catastrophic_error, make_single_error_dict

def clean_ocr_text(ocr_dict):
    """
    Parameters
    ----------
    text : string
        OCRed text we want to clean up.

    Returns
    -------
    clean_text : string
        Same text, but with unicode unknown characters, and anything that's not in
        [A-Za-z0-9], whitespace, or common punctuation

    """
    def _clean(text):
        pattern = re.compile('[^A-Za-z0-9\s!#\$%&\*\(\)_\?\/\+-=\[\]:;\'",\.]+\u2014')
        clean_text = pattern.sub('', text)
        return clean_text

    for scan in ocr_dict.keys():
        ocr_dict[scan] = {k: _clean(article) for k, article in ocr_dict[scan].items()}

    return ocr_dict


def clean_ocr_text_from_json(filename):
    """
    Parameters
    ----------
    filename : string
        name of json to load up. Needs to be in format described in align_json_texts
        signature
    Returns
    -------
    ocr_dict : dictionary
        The same dictionary as above but with each article processed through the
        clean_ocr_text function.

    """
    with open(filename, 'r') as infile:
        ocr_dict = json.load(infile)

    return clean_ocr_text(ocr_dict)


def sanitize_before_aligning(text):
    """
    Parameters
    ----------
    text : string
        Text we want to align with another set.

    Returns
    -------
    sanitized_text: string.
        Same text, with normalized whitespace (any whitespace replaced with a single space)

    """
    text = re.sub('\s+', ' ', text) #Any length whitespace replace with a single space
    text = re.sub('\u2014', '--', text) #em dash replaced with spaces--seem to often be equivalent in transcriptions
    text = re.sub('[\u201c\u201d\u2018]', '"', text)
    text = re.sub('\u2019', '\'', text)
    text = re.sub(' \. ', ' \.', text)
    text = re.sub(' , ', ', ', text)
    text = re.sub(' \' ', '\'', text)

    return text

def clean_string_for_markdown(text):
    text = re.sub('\*', '', text) #Avoiding bolding
    text = text.replace('\\', '') #Avoid backslashes
    text = re.sub('_', '\\_', text) #Avoiding italicizing
    return text

'''Process for outputting a comparison to file, if requested. Three sections: OCR Transcription (just
    the ocr string), then Edits, which displays the ocr string corrected to the gold string with
    deletions in red and additions in green, and finally Human Transcription (just the gold string).
    Underneath those is a count of the number of Homoglyphic, Non-homoglyphic, and Major errors detected.'''
def write_viz_to_file(outfile, gold_text, corrected_texts, disp_strs, error_counts, error_lists, methods):


    disp_strs = [clean_string_for_markdown(disp_str) for disp_str in disp_strs] #Need to filter out astrixes to avoid italisizing/bolding markdown
    corrected_texts = [clean_string_for_markdown(text) for text in corrected_texts]
    gold_text = clean_string_for_markdown(gold_text)

    with open(outfile, 'w') as of:
        of.write('***OCR Transcription -- no corrections***\n <br/>')
        of.write(corrected_texts[-1] + '\n  <br/>')

        of.write('***Edits -- no corrections*** \n <br/>')
        of.write(disp_strs[-1])
        of.write('<br/>\n***List of Subs -- no corrections*** \n <br/>')
        of.write(str(error_lists[-1]))

        for i, method in enumerate(methods[:-1]):
            of.write('</br>\n***OCR Transcription with {}***\n <br/>'.format(method))
            of.write(corrected_texts[i])
            of.write('<br/>\n***Edits -- {}*** \n <br/>'.format(method))
            of.write(disp_strs[i])
            of.write('<br/>\n***List of Subs -- {}*** \n <br/>'.format(method))
            of.write(str(error_lists[i]))

        of.write('<br/> \n***Gold Transcription***\n   <br/>')
        of.write(gold_text)

        of.write('<br/><br/>')
        of.write('***Errors:***<br/>' )
        of.write('***No Correction***: Homoglyphic: {}  Non-Homoglyphic: {}  Major: {}<br/>'.format(
                                error_counts[-1]['homoglyph'], error_counts[-1]['nonhomoglyph'], error_counts[-1]['major']))

        for i, method in enumerate(methods[:-1]):
            of.write('***{}***: Homoglyphic: {}  Non-Homoglyphic: {}  Major: {}'.format(method,
                        error_counts[i]['homoglyph'], error_counts[i]['nonhomoglyph'], error_counts[i]['major']))

    return None

def write_error_lists_to_file(outpath, method_error_lists, spellchecks):

    #Errors are lists of tuples in the form [(gold_chr, orc_chr), (gold_chr, ocr_chr), ... ]
    #Each indicating an instance where the character <gold_chr> has been mistranscribed as <ocr_chr>
    for errors, method in zip(method_error_lists, spellchecks):
        if method != '':
            method_outpath = outpath[:-4] + '_' + method + '.npy'
        else: method_outpath = outpath

        max_ord = max([max(ord(x[0]), ord(x[1])) for x in errors])
        error_counts = np.zeros(shape = (max_ord + 1, max_ord + 1))

        for gold_chr, ocr_chr in errors:
            error_counts[ord(gold_chr), ord(ocr_chr)] += 1

        assert error_counts.sum() == len(errors)

        np.save(method_outpath, error_counts)



def align_json_texts(ocr_filepath, gold_filepath, ids = None, outfile = None, \
                     spellchecks = [], list_error_len = 0, error_list_outpath = None):
    """
    Parameters
    ----------
    ocr_filepath : string
        Path to json file with OCR transcriptions. Needs to be in the format:
            Needs to be in the format:
                {scan1_id: {article1_id: <article1_text>,
                         article2_id: <article2_text>,
                         ....},
                 scan2_id: {article1_id: <article1_text>,
                            ... },
                 ...
                 }
    gold_filepath : string
        Path to json/coco file with gold (hand transcribed) data from newspaper scans.

    ids: list of ints
        If you want, you can pass in a list of annotation ids and, instead of going through all the texts
        in the ocr file the function will just count the ones included in the list

    outfile: string
        If you want to visualize the errors in a specific passage, make sure that len(ids) = 1,
        and then pass an outfile in. That file will be written with a markdown (shows up well in Atom) version
        of the errors identified in the passage.

    spellchecks: a list of spellchecking algorithms to be applied to the ocr-ed text. Options are:
            'neuspell' - Neuspell spell checking

    Returns
    -------
    error_counts: dict
        Dictionary in format
            {
                            'homoglyph': x,
                            'nonhomoglyph': x,
                            'major': x,
                            'none': x,
                            'catastrophic': x
            }
        With the number of each type of error counted up in the categories. The length an error
        must exceed to be classified as 'major' is specified in align.py. 'none' are not really errors,
        just a placeholder that should be ignored in all analysis. 'catastrophic' refers to articles/boxes
        that were completely mistranscribed, where one (but not both) of the ocr or gold strings are length 0,
        or where the ocr transcription is > 2x or < .5x as long as the gold transcription

    """
    if outfile is not None and len(ids) != 1:
        raise ValueError('Can only write to file if a single id is specified!')
    if outfile is not None and len(spellchecks) > 0:
        raise ValueError('Can only write to file if either one or zero spellchecks are specified!')

    with open(gold_filepath, 'r') as infile:
        gold_dict = json.load(infile)['annotations']

    #Flatten out the gold transcriptions--get them indexed only by annotation id
    gold_dict = {int(anno['id']): anno['text'] for anno in gold_dict}

    spellchecks.append('')

    #If we're writing to file for visualization/debugging, need to be saving info as it comes out
    if outfile is not None:
        method_error_counts = []
        method_disp_strs = []
        corrected_texts = []
        method_error_lists = []
    elif error_list_outpath is not None:
        method_error_lists = []

    #Want to count errors/create visualzations for each of the spell checking methods provided
    total_chars = 0
    for method in spellchecks:
        #Assumes that spell checked files are saved in the same directory as <original_file>_<spellchecking_method>.json
        filepath = ocr_filepath[:-5] + '_{}.json'.format(method) if method != '' else ocr_filepath
        ocr_dict = clean_ocr_text_from_json(filepath)

        #This is just 'flipping' the ocr dict
        ocr_dict = {int(k): ocr_dict[img][k] for img in ocr_dict.keys() for k, v in ocr_dict[img].items() }

        if ids is None:
            ids = list(ocr_dict.keys())

        error_counts = Counter()
        error_list = []

        #Calls the align_texts function for the spell checking method (or not original version) and the
        # gold standard/ground truth text supplied
        for text_id in ids:
            ocr_clean, gold_clean = sanitize_before_aligning(ocr_dict[text_id]), sanitize_before_aligning(gold_dict[text_id])
            total_chars += len(ocr_clean)
            if check_for_catastrophic_error(ocr_clean, gold_clean):
                text_str, text_counts, errors = '', make_single_error_dict('catastrophic'), []
            else:
                text_str, text_counts, errors = align_texts(ocr_clean, gold_clean, list_error_len = list_error_len)

            error_counts.update(text_counts)
            error_list.extend(errors)

        #Put together the eventual visualization to point out errors
        if outfile is not None:
            method_error_counts.append(dict(error_counts))
            method_disp_strs.append(text_str)
            method_error_lists.append(error_list)
            corrected_texts.append(sanitize_before_aligning(ocr_dict[text_id]))

        elif error_list_outpath is not None:
            method_error_lists.append(error_list)

        print(method, dict(error_counts), len(error_list))

    if outfile is not None:
        write_viz_to_file(outfile, sanitize_before_aligning(gold_dict[ids[0]]), corrected_texts,
                          method_disp_strs, method_error_counts, method_error_lists, spellchecks)

    if error_list_outpath is not None:
        write_error_lists_to_file(error_list_outpath, method_error_lists, spellchecks)

    return None

#Debugging
# os.chdir(r'C:\Users\bryan\Documents\NBER\OCR_error_correction\data')
# align_json_texts('image_ocr_results_symspell.json', 'chronam_gt_coco.json', [108], list_error_len=1, outfile= 'color_highlighting_test.txt')