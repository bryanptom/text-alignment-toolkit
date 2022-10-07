# -*- coding: utf-8 -*-
"""
Created on Wed Jul 13 15:29:12 2022

@author: bryan

Method to do the heavy lifting comparing ocr-ed
and hand-transcribed text, finding and classifying errors,
creating usable lists and counts of errors, and visualizable text
displaying those errors.

And more!!

Not actually more, that is all it does
"""

from difflib import SequenceMatcher
from collections import Counter
from homoglyph_checker import is_error_homoglyphic
import re
import string

'''HTML Color Sequence Tags'''
HTML_red    = '<span style="color:red">'
HTML_yellow    = '<span style="color:yellow">'
HTML_green    = '<span style="color:green">'
HTML_blue    = '<span style="color:blue">'
HTML_end    = '</span>'
strike = '~~'
bold = '**'

color_codes = {'equal': '',
               'insert': HTML_green,
               'replace': HTML_red,
               'delete': HTML_red}

end_codes = {'equal': '',
            'insert': HTML_end,
            'replace': HTML_end,
            'delete': '</span>'}

'''Constants--These are all arbitrary/tunable'''
MIN_COMBO_DIST = 10
MIN_EQUAL_DIST = 10
MIN_MAJOR_ERROR_CHARS = 5

def combine_step_groups(steps):
    step_groups = []
    cur_group = []

    flag_equal_longer_ten = False

    for i in range(len(steps)):

        if steps[i][0] == 'equal':
            if steps[i][2] - steps[i][1] > MIN_EQUAL_DIST:
                step_groups.append(cur_group)
                step_groups.append([steps[i]])
                cur_group = []

                flag_equal_longer_ten = True
            else:
                cur_group.append(steps[i])
        else:
            cur_group.append(steps[i])

    step_groups.append(cur_group)
    return step_groups, flag_equal_longer_ten

def make_single_error_dict(error_type):
    error_counts = {
                    'homoglyph': 0,
                    'nonhomoglyph': 0,
                    'major': 0,
                    'none': 0,
                    'catastrophic': 0
                    }
    error_counts[error_type] += 1
    return error_counts

'''
    Nah...we need to run the spellchecking as a batch on all texts we're comparing,
   before actually passing individual ocr and gold texts into a function. Some of
   the spellcheckers, particularly NeuSpell, take far too long to load in the models
   to be usable in this context--running each one on individual texts can take like
   2min/article '''
'''
def align_texts_with_spellchecking(ocr, gold, outfile = None, spellchecks = None):
    if outfile is not None and len(spellchecks) > 1:
        raise ValueError('Cannot output to file if more than one spellchecking method supplied!')

    if outfile is not None:
        if spellchecks is None or len(spellchecks) == 0:
            return align_texts(ocr, gold, outfile = outfile)
        else:
            method = spellchecks[0]
            return align_texts(apply_spellchecking(ocr, method), gold, outfile = outfile, spellcheck_method = method)
    else:
        return [align_texts(apply_spellchecking(ocr, spellcheck)) for spellcheck in spellchecks]
'''

'''Checking for some simple conditions that mark that the ocr has gone serioulsy wrong'''
def check_for_catastrophic_error(ocr, gold):
    try:
        if len(ocr) == 0 and len(gold) == 0: return True #??? Not really sure what appropriate behavior is here
        elif len(ocr) == 0: raise ValueError('OCR Text has length 0!')
        elif len(gold) == 0: raise ValueError('Gold Text has lenght 0!')

        if len(gold) > 10 and len(ocr) > 10:
            if len(ocr) - len(gold) > len(gold): raise ValueError('OCR text > 2x longer than gold text')
            if len(gold) - len(ocr) > len(ocr): raise ValueError('gold text > 2x longer than OCR text')

        return False
    except ValueError:
        return True

def align_texts(ocr, gold, list_error_len = 0):
    """
    Parameters
    ----------
    ocr : str
        String with errors (possibly) in it.
    gold : str
        String to compare against.

    Raises
    ------
    ValueError
        Errors if either one of the strings has length 0 or if the strings are too far apart in length.
        Further on I think I'll write into the code for processing these in batches to call an error from
        this function like a "catestrophic" error or something like that, since it indicates that something is
        very wrong with the transcription

    Returns
    -------
    TYPE
        disp_str: The markdown string showing the errors. This has HTML tags to turn the deleted
        characters red and the inserted characters green

        error_counts: Dict. Dictionary in the format:
                {
                                'homoglyph': x,
                                'nonhomoglyph': x,
                                'major': x,
                                'none': x
                }
        Counting the number of the errors of each type identified in the strings passed. Major are
        errors involving more than MIN_MAJOR_ERROR_CHARS characters
    """


    '''Create the set of opcodes/steps for editing the ocr string into the gold one'''
    sm = SequenceMatcher(isjunk = None, a = ocr, b = gold, autojunk = False)
    steps = sm.get_opcodes()


    '''Form groups of opcodes (which tell you how the OCR string needs to be edited to
    make the ground truth one). The components of each group will be reprocessed together
    as a smaller string. We do this because the opcodes tend to be inaccurate with larger
    strings but more accurate/granular with shorter ones.'''
    step_groups, continue_flag = combine_step_groups(steps)

    '''Helpers to process the opcodes into usable data'''

    ''' Finds the actual error (which characters have been replaced by which other characters?)
    Returns the error only if reporting conditions are met--as of now that's if both gold text
    and ocred text in the error are a set length '''
    def _get_step_error(cur_step):
        edit_type, ocr0, ocr1, gold0, gold1 = cur_step
        if edit_type != 'replace':
            return []
        elif ocr1 - ocr0 == list_error_len and gold1 - gold0 == list_error_len:
            return [(gold[gold0:gold1], ocr[ocr0:ocr1])]
        else:
            return []

    '''Figures out if an error is major, homoglyphic, or non-homoglyphic'''
    def _get_step_error_type(cur_step):
        edit_type, ocr0, ocr1, gold0, gold1 = cur_step
        '''Anything with > MIN_MAJOR_ERROR_CHARS characters out of place is considered a major error'''
        if edit_type == 'equal':
            return 'none'
        elif max(ocr1 - ocr0, gold1 - gold0) > MIN_MAJOR_ERROR_CHARS:
            return 'major'
        elif edit_type in ['insert', 'delete']:
            return 'nonhomoglyph'
        else:
            return is_error_homoglyphic(ocr[ocr0:ocr1], gold[gold0:gold1])

    '''Gets the display string for a particular opcode/step'''
    def _get_step_disp(cur_step):
        edit_type, ocr0, ocr1, gold0, gold1 = cur_step

        #Constructs the 'inside' portion of the display string (the part that will be surrounded by html markers)
        if edit_type == 'equal' or edit_type == 'insert':
            cur_str = gold[gold0:gold1]
        elif edit_type == 'delete':
            cur_str = ocr[ocr0:ocr1]
        else:
            cur_str = ocr[ocr0:ocr1] + HTML_end + HTML_green + gold[gold0:gold1]

        #Replace spaces with underscores in insert operations to make them more obvious
        if edit_type in ['insert', 'delete'] and cur_str.count(' ') < 4:
            cur_str = re.sub(' ', '_', cur_str)

        return color_codes[edit_type] + cur_str + end_codes[edit_type], _get_step_error_type(cur_step),  \
                        _get_step_error(cur_step)

    '''Goes through a few common cases to determine whether the error at hand is 'real'
    (i.e. needs fixing) or is just an artifact of spell checking/strange punctuation'''
    def _is_error_real(cur_step):
        edit_type, ocr0, ocr1, gold0, gold1 = cur_step

        if ocr[ocr0:ocr1].lower() == gold[gold0:gold1].lower():
            return False
        elif edit_type == 'insert' and gold[gold0:gold1] == '- ':
            return False
        elif edit_type == 'insert' and all([i in string.punctuation or i == ' ' for i in gold[gold0:gold1]]):
            return False
        else:
            return True

    '''Gets the display string and error counts for a group of opcodes
    Recurses if necessary, sending everything in the group's coverage into a
    new call of align_texts. Needed because with large strings the opcodes aren't very granular'''
    def _process_step_group(cur_group):
        if len(cur_group) == 0:
            return '', make_single_error_dict('none'), []
        elif len(cur_group) == 1 and cur_group[0][0] in ['equal', 'delete', 'insert']:
            # if _is_error_real(cur_group[0]):
            step_str, error_type, error = _get_step_disp(cur_group[0])
            return step_str, make_single_error_dict(error_type), error
            # else:
            #     return ocr[cur_group[0][1]:cur_group[0][2]], make_single_error_dict('none'), []
        else:
            ocr_start, ocr_end = cur_group[0][1], cur_group[-1][2]
            gold_start, gold_end = cur_group[0][3], cur_group[-1][4]
            return align_texts(ocr[ocr_start:ocr_end], gold[gold_start:gold_end], list_error_len = list_error_len)

    '''A second check to confirm that it is indeed time to process individual steps.
    Sometimes the sequence matcher object can get badly confused.

    NOPE, NOT NEEDED: This was caused by some other faulty processes
    '''
    # if not continue_flag and len(ocr) > 100:
    #     os, gs, size = sm.find_longest_match(0, len(ocr), 0, len(gold))
    #     if size > 50:
    #         print('used check 2!')
    #         oe = os + size
    #         ge = gs + size
    #         continue_flag = True
    #         step_groups = [('replace', 0, os, 0, gs), ('equal', os, oe, gs, ge), ('replace', oe, len(ocr), ge, len(gold))]




    '''Continue_Flag signals whether we've reached the bottom of the recursion or not.
    Determined by the presence of at least one 'equal' section of length at least MIN_EQUAL_DIST.
    If there are no long equal sections left in the strings, we process the steps directly'''
    disp_str = ''
    error_list = []

    if continue_flag:
        error_counter = Counter()

        for group in step_groups:
            group_str, group_counts, group_errors = _process_step_group(group)
            disp_str += group_str
            error_counter.update(group_counts)
            error_list.extend(group_errors)

        error_counts = dict(error_counter)
    else:
        error_counts = make_single_error_dict('none')

        for step in steps:
            # if _is_error_real(step):
            step_str, error_type, error = _get_step_disp(step)
            disp_str += step_str
            error_counts[error_type] += 1
            error_list.extend(error)
            # else:
            #     disp_str += ocr[step[1]:step[2]]


    return disp_str, error_counts, error_list