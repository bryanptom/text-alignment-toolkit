'''
Analysis script checking out the results saved in error_counts files
'''

import numpy as np
import json

fp = r'C:\Users\bryan\Documents\NBER\OCR_error_correction\data\error_counts_symspell.npy'
symspell_counts = np.load(fp)

fp = r'C:\Users\bryan\Documents\NBER\OCR_error_correction\data\error_counts_new_visual_homoglyph.npy'
homoglyph_counts = np.load(fp)

fp = r'C:\Users\bryan\Documents\NBER\OCR_error_correction\data\error_counts.npy'
reg_counts = np.load(fp)

homoglyphs_path = r'C:\Users\bryan\Documents\NBER\OCR_error_correction\code\utils\homoglyph_list.json'
with open(homoglyphs_path, 'r') as infile:
    glyphs = json.load(infile)

def create_glyphs_dict(glyphs):
    i = 0
    g_dict = {}
    while glyphs[i]['sim_score'] > 0:
        if glyphs[i]['a'] not in g_dict.keys():
            g_dict[glyphs[i]['a']] = {}
        if glyphs[i]['b'] not in g_dict.keys():
            g_dict[glyphs[i]['b']] = {}
        g_dict[glyphs[i]['a']][glyphs[i]['b']] = glyphs[i]['sim_score']
        g_dict[glyphs[i]['b']][glyphs[i]['a']] = glyphs[i]['sim_score']
        i += 1

    return g_dict

g_dict = create_glyphs_dict(glyphs)

reg_counts_total = 0
for i in range(reg_counts.shape[0]):
    for j in range(reg_counts.shape[0]):
        if chr(i).isalnum() and chr(j).isalnum():
            reg_counts_total += g_dict.get(chr(i), {}).get(chr(j), 0) * reg_counts[i, j]

# print(reg_counts_total)
print('Reg Avg')
print(reg_counts_total / reg_counts.sum())

sym_counts_total = 0
for i in range(symspell_counts.shape[0]):
    for j in range(symspell_counts.shape[0]):
        if chr(i).isalnum() and chr(j).isalnum():
            sym_counts_total += g_dict.get(chr(i), {}).get(chr(j), 0) * symspell_counts[i, j]

# print(sym_counts_total)
print('Symspell Avg')
print(sym_counts_total / symspell_counts.sum())

# hom_counts_total = 0
# for i in range(homoglyph_counts.shape[0]):
#     for j in range(homoglyph_counts.shape[0]):
#         if chr(i).isalnum() and chr(j).isalnum():
#             hom_counts_total += g_dict.get(chr(i), {}).get(chr(j), 0) * homoglyph_counts[i, j]

# # print(hom_counts_total)
# print(hom_counts_total / homoglyph_counts.sum())

print('Corrections:')
total = 0
reg_total = 0
for glyph in glyphs[:200]:
    try:
        if symspell_counts[ord(glyph['a']), ord(glyph['b'])] + symspell_counts[ord(glyph['b']), ord(glyph['a'])] > 0:
                print(glyph['a'], glyph['b'])
                print('Similarity: {}'.format(round(glyph['sim_score'], 2)))
                print('No Correction: {}'.format(reg_counts[ord(glyph['a']), ord(glyph['b'])] + reg_counts[ord(glyph['b']), ord(glyph['a'])]))
                print('Symspell: {}'.format(symspell_counts[ord(glyph['a']), ord(glyph['b'])] + symspell_counts[ord(glyph['b']), ord(glyph['a'])]))
                total += symspell_counts[ord(glyph['a']), ord(glyph['b'])] + symspell_counts[ord(glyph['b']), ord(glyph['a'])]
                reg_total += reg_counts[ord(glyph['a']), ord(glyph['b'])] + reg_counts[ord(glyph['b']), ord(glyph['a'])]

                # print('Homoglyph Checker: {}'.format(homoglyph_counts[ord(glyph['a']), ord(glyph['b'])] + homoglyph_counts[ord(glyph['b']), ord(glyph['a'])]))
    except IndexError:
        pass

print(f'Homoglyph Errors: {total}')
print(f'Total Errors: {symspell_counts.sum()}')
print(f'No correction total {reg_counts.sum()}')
print(f'No correction errors: {reg_total}')
    # top = np.unravel_index(np.argmax(counts, axis = None), counts.shape)
    # top_n.append((chr(top[0]), chr(top[1]), counts[top[0], top[1]]))
    # counts[top[0], top[1]] = 0

