# -*- coding: utf-8 -*-
"""
Created on Mon Jul 11 13:22:00 2022

@author: bryan
"""
import sys
import re
sys.path.insert(1, '../../neuspell')
from neuspell import available_checkers, BertChecker

print(available_checkers())
checker = BertChecker()
checker.from_pretrained()


with open(r'..\data\sample_article.txt', 'r') as infile:
    text = infile.read()

print(text[:300])
text = re.sub('\s', ' ', text)
pattern = re.compile('[^A-Za-z0-9\s]+')
text_filtered = pattern.sub('', text)


