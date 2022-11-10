'''
Created on Dec 16, 2015

@author: Severin Denk
'''
import re
import os
string_pattern = re.compile(r'[^0-9^\.^\+^\-^e^d]')
integer_pattern = re.compile(r'^(([+-])?\d+)$')
tuple_pattern = re.compile(r'(?<=_)\d*(?=tuple)')
bool_pattern = re.compile(r'^[tfTF]$')
tuple_number_pattern = re.compile(r'(?<=^)[\d]*(?=;)')

EOLCHARF = '\n'  # For files.
EOLCHART = os.linesep
def test_float(val, mode=0):
    if(mode == 1):
        val = val.split(',')
    else:
        val = [val]
    for i in range(len(val)):
        if(re.search(string_pattern, val[i])):
            return False
        val[i] = val[i].replace('e', 'd')
        if(val[i].count('d') > 1):
            return False
        if(val[i].count('.') > 1):
            return False
        if(val[i].count('+') > 1):
            return False
        if('d' in val[i]):
            if(not re.search(integer_pattern, val[i].split('d')[1])):
                return False
            else:
                val[i] = val[i].split('d')[0]
        if('.' in val[i]):
            part_list = val[i].split('.')
            for i in range(2):
                if(len(part_list[i]) > 0):
                    if(not re.search(integer_pattern, part_list[i])):
                        return False
    return True

def test_integer(val, mode=0):
    if(mode == 1):
        val = val.split(',')
    else:
        val = [val]
    for i in range(len(val)):
        if(not re.search(integer_pattern, val[i])):
            return False
    return True
