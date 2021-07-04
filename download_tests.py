#!/usr/bin/python3

LINK = "https://www.dropbox.com/sh/nx3tnilzqz7df8a/AAB-kg7ky4OKjwrsftb_238ka/abc207/A?dl=0&subfolder_nav_tracking=1"

import sys, requests, re, os, shutil, string
from bs4 import BeautifulSoup
from zipfile import ZipFile
from tqdm import tqdm

sip_folder = "./"
utils_folder = sip_folder + "utils/"

def download_testcases(link):
    link = link.replace('dl=0', 'dl=1')
    print("Downloading zip with testcases")
    if not os.path.exists(utils_folder):
        os.makedirs(utils_folder)
    with requests.get(link, stream=True) as r:
        with open(utils_folder + "testcases.zip", "wb") as f:
            for block in tqdm(r.iter_content(1024)):
                f.write(block)

    print("Reorganizing testcases")
    with ZipFile(utils_folder + "testcases.zip", 'r') as zip_ref:
        zip_ref.extractall(utils_folder)

        for test_type in ["in", "out"]:
            if os.path.isdir(utils_folder + test_type):
                used_number = {}
                used_number[0] = True
                sample_used_number = {}
                sample_used_number[0] = True
                for test in os.listdir(utils_folder + test_type):
                    is_sample = False
                    number = 0
                    for prefix in ["s", "sample", "0_", "a", "sample_"]:
                        if re.search("^" + prefix + "\d+\.txt$", test):
                            number = int(re.findall("^" + prefix + "(\d+)", test)[0])
                            is_sample = True
                            if number in sample_used_number:
                                number = 1
                            while number in sample_used_number:
                                number += 1
                            sample_used_number[number] = True
                            break

                    if not is_sample:
                        if re.search("\d+\w+\d+", test):
                            number = int(re.findall("\d+\w+(\d+)", test)[0])
                        elif re.search("\d+", test):
                            number = int(re.findall("(\d+)", test)[0])
                        else:
                            assert False
                        if number in used_number:
                            number = 1
                        while number in used_number:
                            number += 1
                        used_number[number] = True

                    new_name = "test"
                    if is_sample:
                        new_name += "0" + string.ascii_lowercase[number - 1]
                    else:
                        new_name += str(number)
                    print("- Renaming", test_type + '/' + test, "to", new_name + '.' + test_type)
                    os.rename(utils_folder + test_type + '/' + test, sip_folder + test_type + '/' + new_name + '.' + test_type)
    shutil.rmtree(utils_folder)

download_testcases(LINK)

