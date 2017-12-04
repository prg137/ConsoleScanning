"""General utilites used by mulitple ci files"""
from __future__ import print_function

import os
import datetime
from termcolor import colored

def color_print(string, color_str="cyan", bkgd=None, end_char="\n"):
    """performs a colored print"""
    if bkgd is not None:
        print(colored(string, color_str, bkgd), end=end_char)
    else:
        print( colored(string, color_str), end=end_char)

def open_file(directory, filename):
    """open a file object and add a timestamp"""
    if(os.path.exists(directory) is False):
        path_elements = directory.split('/')
        working_path = ''
        for element in path_elements:
            working_path += element
            if(os.path.exists(working_path) is False):
                os.mkdir(working_path)
            working_path += '/'

    file_obj = open(directory + '/' + filename, "a")
    timestamp = datetime.now().strftime("%Y%m%d_%H:%M:%S - %A")
    file_obj.write("\n\n----File opened for appending at {}----\n".format(timestamp))
    return file_obj

