# -*- coding: utf-8 -*-
"""
Created on Thu Jul 14 17:40:56 2022

@author: bryan

Super-method and associated individual spell checking functions
to apply different spell checking techniques to OCR-ed text. A call looks like:

    apply_spellcheckings_json('<ocr_filepath>.json', ['<method1>, <method2>', ....])

Where the ocr_filepath.json file has to have the format:
    {scan1_id: {article1_id: <article1_text>,
             article2_id: <article2_text>,
             ....},
     scan2_id: {article1_id: <article1_text>,
                ... },
     ...
     }
"""

import json
import time
import pkg_resources
from tqdm import tqdm
from difflib import SequenceMatcher

# from neuspell import BertChecker, CnnlstmChecker, SclstmChecker
from symspellpy import SymSpell, Verbosity
from homoglyph_spell_check_utils import create_common_abbrev, create_worddict, create_homoglyph_dict, visual_spell_checker
import contextualSpellCheck
import spacy
from align_texts import clean_ocr_text

class spellcheck:

    preprocessing_methods = {'align_cleaning': clean_ocr_text}

    def __init__(self, filepath, preprocessing = None):
        with open(filepath, 'r') as infile:
            self.ocr_dict = json.load(infile)

        self.load_time = 0
        self.run_time = 0
        self.checked_dict = None
        self.outpath = filepath[:-5]
        self.preprocessing = preprocessing

        if self.preprocessing is not None:
            self._preprocess()

    def _preprocess(self):
        self.ocr_dict = self.preprocessing_methods[self.preprocessing](self.ocr_dict)

    def spellcheck(self):

        loadin_start = time.time()
        self._load_checker()
        self.load_time = time.time() - loadin_start

        run_start = time.time()
        self._run_checker()
        self.run_time = time.time() - run_start

    def write_results(self):
        with open(self.outpath, 'w') as outfile:
            json.dump(self.ocr_dict, outfile)
        print('load time: {}'.format(self.load_time))
        print('run time: {}'.format(self.run_time))


# class neuspell_checker(spellcheck):

#     checker_dict = {'bert': BertChecker,
#                     'cnnlstm': CnnlstmChecker,
#                     'sclstm': SclstmChecker }

#     def __init__(self, filepath, checker_type = 'bert', seg_size = 'sentence'):
#         super().__init__(filepath)
#         self.outpath += '_neuspell_{}_{}.json'.format(checker_type, seg_size)
#         self.seg_size = seg_size
#         self.checker_type = checker_type



#     def _load_checker(self):
#         self.checker = self.checker_dict[self.checker_type]()
#         self.checker.from_pretrained()

#     def _run_checker(self):

#         for scan in tqdm(list(self.ocr_dict.keys())[:1]):
#             for k, article in self.ocr_dict[scan].items():
#                 try:
#                     if len(article) > 0:
#                         if self.seg_size == 'sentence':
#                             self.ocr_dict[scan][k] = self._correct_article_sentence(article)
#                         elif self.seg_size == 'paragraph':
#                             self.ocr_dict[scan][k] = self._correct_article_paragraph(article)
#                         elif self.seg_size == 'article':
#                             self.ocr_dict[scan][k] = self.checker.correct(article)

#                     else:
#                         self.ocr_dict[scan][k] = ''
#                 except ValueError:
#                     self.ocr_dict[scan][k] = ''

#     def _correct_article_sentence(self, article):
#         return '.'.join([self.checker.correct(sentence) for sentence in
#                                                   article.split('.') if len(sentence) > 0])

#     def _attach_string_chunk(self, string_til_now, new_chunk):
#         sm = SequenceMatcher(a = string_til_now, b = new_chunk, autojunk = False)
#         s_string, s_chunk, size = sm.find_longest_match(0, len(string_til_now), 0, len(new_chunk))
#         string_with_addition = string_til_now[:s_string + size] + new_chunk[s_chunk + size:]
#         return string_with_addition

#     def _correct_article_paragraph(self, article):
#         if len(article) < 700:
#             return self.checker.correct(article)
#         else:
#             corrected = ''
#             for i in range(len(article) // 250):
#                 s_idx = i * 250
#                 corrected_chunk = self.checker.correct(article[s_idx: s_idx + 500])

#                 if len(corrected) == 0:
#                     corrected = corrected_chunk
#                 else:
#                     corrected = self._attach_string_chunk(corrected, corrected_chunk)

#             final_chunk = self.checker.correct(article[-500:])
#             return self._attach_string_chunk(corrected, final_chunk)


class symspell_checker(spellcheck):
    def __init__(self, filepath):
        super().__init__(filepath)
        self.outpath += '_symspell.json'

    def _load_checker(self):
        self.checker = SymSpell()
        dictionary_path = pkg_resources.resource_filename(
            'symspellpy', 'frequency_dictionary_en_82_765.txt'
        )
        self.checker.load_dictionary(dictionary_path, 0, 1)

        dictionary_path = pkg_resources.resource_filename(
            "symspellpy", "frequency_bigramdictionary_en_243_342.txt"
        )
        self.checker.load_bigram_dictionary(dictionary_path, 0, 2)

    def _run_checker(self):
        for scan in self.ocr_dict.keys():
            for k, article in self.ocr_dict[scan].items():
                try:
                    if len(article) > 0:
                        sentence_corrs = []
                        sentences = article.split('.')

                        for sentence in sentences:
                            corrs = []
                            for input_term in sentence.split():
                                suggestions = self.checker.lookup(input_term, Verbosity.CLOSEST, max_edit_distance=1, include_unknown=True,
                                                                transfer_casing=True)
                                corrs.append(suggestions[0].term)
                            sentence_corrs.append(' '.join(corrs))

                        self.ocr_dict[scan][k] = '. '.join(sentence_corrs)
                    else:
                        self.ocr_dict[scan][k] = ''
                except ValueError:
                    print(article)
                    self.ocr_dict[scan][k] = ''

class symspell_sentence_checker(symspell_checker):
    def __init__(self, filepath):
        super().__init__(filepath)

    def _run_checker(self):
        for scan in self.ocr_dict.keys():
            for k, article in self.ocr_dict[scan].items():
                try:
                    if len(article) > 0:
                        sentence_corrs = []
                        sentences = article.split('.')

                        for sentence in sentences:
                            corr = self.checker.lookup_compound(sentence, max_edit_distance=2, transfer_casing=True)[0]
                            sentence_corrs.append(corr.term)

                        self.ocr_dict[scan][k] = '. '.join(sentence_corrs)
                    else:
                        self.ocr_dict[scan][k] = ''
                except ValueError:
                    print(article)
                    self.ocr_dict[scan][k] = ''


class spacy_checker(spellcheck):

    def __init__(self, filepath):
        super().__init__(filepath)
        self.outpath += '_spacy.json'

    def _load_checker(self):
        self.checker = spacy.load('en_core_web_sm')
        contextualSpellCheck.add_to_pipe(self.checker)

    def _run_checker(self):
        for scan in self.ocr_dict.keys():
            for k, article in self.ocr_dict[scan].items():
                try:
                    if len(article) > 0:
                        doc = self.checker(article)
                        self.ocr_dict[scan][k] = doc._.outcome_spellCheck
                    else:
                        self.ocr_dict[scan][k] = ''
                except ValueError:
                    print(article)
                    self.ocr_dict[scan][k] = ''
class vs_checker:

    def __init__(self, worddict, homoglyph_dict, abbrevset):
        self.worddict, self.homoglyph_dict, self.abbrevset = worddict, homoglyph_dict, abbrevset

    def check_sentence(self, sentence):
        return visual_spell_checker(sentence, self.worddict, self.homoglyph_dict, self.abbrevset)

class visual_homoglyph_checker(spellcheck):

    def __init__(self, filepath, homoglyphs_path = r'C:\Users\bryan\Documents\NBER\OCR_error_correction\code\utils\homoglyph_list.json', sensitivity = 0.35, preprocessing = 'align_cleaning'):
        super().__init__(filepath)
        self.outpath += 'new_visual_homoglyph.json'
        self.homoglyphs_path = homoglyphs_path
        self.sensitivity = sensitivity

    def _load_checker(self):
        worddict = create_worddict()
        homoglyph_dict = create_homoglyph_dict(homoglyph_fp = self.homoglyphs_path)
        abbrevset = create_common_abbrev()
        self.checker = vs_checker(worddict, homoglyph_dict, abbrevset)

    def _run_checker(self):
        for scan in tqdm(self.ocr_dict.keys()):
            for k, article in self.ocr_dict[scan].items():
                try:
                    if len(article) > 0:
                        self.ocr_dict[scan][k] = '. '.join([self.checker.check_sentence(sentence)  for sentence in
                                                      article.split('.') if len(sentence) > 0])
                    else:
                        self.ocr_dict[scan][k] = ''
                except ValueError:
                    self.ocr_dict[scan][k] = ''