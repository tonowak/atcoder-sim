#!/usr/bin/python3

import sys
import requests
from bs4 import BeautifulSoup
import re
import os
import subprocess
import shutil
import string
from zipfile import ZipFile
from tqdm import tqdm

class Paczkarka:
    atcoder_link = "https://atcoder.jp/"
    dropbox_link = "https://www.dropbox.com/sh/arnpe0ef5wds8cv/AAAk_SECQ2Nc6SVGii3rHX6Fa?dl=0"
    logfile = open(os.devnull, 'w')

    def create_dirs(self, args):
        for dir in args:
            if not os.path.exists(dir):
                os.makedirs(dir)

    def get_problem_info(self, bs):
        print("Getting problem info")
        for i in bs.find_all('p'):
            if i.string and "Time Limit" in i.string:
                numbers = re.findall("\d+\.*\d*", i.string)
                self.time_limit, self.memory_limit = numbers
                print("- Time limit:", self.time_limit, "s (not using, setting TL automatically)")
                if int(self.memory_limit) <= 256:
                    print("- Memory limit:", self.memory_limit, "MB")
                else:
                    print("- Memory limit:", self.memory_limit, "MB, but lowering to 256 MB")
                    self.memory_limit = "256"

        for i in bs.find_all("span", {"class": "h2"}):
            self.problem_name = i.contents[0].strip()
            print("- Problem name:", self.problem_name)

    def name_to_dir(self, name):
        charPL = "ŻÓŁĆĘŚĄŹŃżółćęśąźń -()'"
        charnoPL = "ZOLCESAZNzolcesazn__[]_"
        name = name.translate(str.maketrans(charPL, charnoPL))
        for it in range(2):
            name = name.replace("__", "_")
        return name

    def remove_trailing(self, string):
        while string and string[0] == '\n':
            string = string[1:]
        while string and string[-1] == '\n':
            string = string[:-1]
        if string:
            string = string.replace("\n\n\n", "\n\n")
            string = string.replace("\"", "\"{}")
            string = string.replace("#", "\\#")
            string = string.replace("≦", " \\leq ")
            string = string.replace("≤", " \\leq ")
        return string

    image_cnt = 0
    def save_image(self, link):
        self.image_cnt += 1
        filename = "doc" + str(self.image_cnt) + ".png"
        print("- Downloading image", filename)
        img_data = requests.get(link).content
        with open(self.doc_folder + filename, "wb") as file:
            file.write(img_data)
        return filename

    def extract_paragraph(self, bs):
        paragraph = ""
        title = ""
        example = ""
        for content in bs.contents:
            # print(content.name)
            if content.name is None:
                paragraph += content.string
                continue
            n = content.name
            if n == "p":
                paragraph += self.extract_paragraph(content)[0]
            elif n == "h3":
                title = content.string
            elif n == "pre":
                example += self.extract_paragraph(content)[0]
            elif n == "var":
                paragraph += "$" + content.string + "$"
            elif n == "code":
                paragraph += "{\\ttfamily " + content.string + "}"
            elif n == "br":
                paragraph += "\n\n"
            elif n == "strong":
                paragraph += "\\textbf{" + content.string + "}"
            elif n == "em":
                paragraph += "\\textit{" + content.string + "}"
            elif n == "div":
                paragraph += self.extract_paragraph(content)[0]
            elif n == "ul" or n == 'ol':
                paragraph += "\\begin{itemize}\n"
                for li in content.findAll("li"):
                    paragraph += "\t\item " + self.extract_paragraph(li)[0] + "\n"
                paragraph += "\\end{itemize}\n"
            elif n == "img":
                link = content["src"]
                filename = self.save_image(link)
                paragraph += "\n\\includegraphics[scale=0.75]{" + filename[:-4] + "}\n"
            else:
                print("Error: not recognizing", n)
                print(content.prettify())
                assert False
        return [paragraph, title, example]

    def compile_statement(self, latex_dir, latex_file, pdf_file):
        print("Compiling " + latex_dir + latex_file)
        shutil.copyfile("sim-statement.cls", latex_dir + "sim-statement.cls")
        for it in range(2):
            subprocess.call(["cd " + latex_dir + " && pdflatex --interaction nonstopmode " + latex_file],
                    shell=True, stdout=self.logfile, stderr=self.logfile)
            # subprocess.call(["cp " + latex_dir + latex_file + " " + pdf_file],
                    # shell=True, stdout=self.logfile, stderr=self.logfile)

    def create_statement(self, bs):
        print("Creating latex file")
        inter = ""
        input = ""
        output = ""
        examples = []
        example_notes = []

        for statement in bs.find_all("span", {"class": "lang-en"}):
            for part in statement.find_all("div", {"class": "part"}):
                # print(part.section.prettify())
                got = self.extract_paragraph(part.section)
                for i in range(3):
                    got[i] = self.remove_trailing(got[i])
                # print(got)

                if got[1] and "Sample" not in got[1]:
                    if "Output" in got[1]:
                        output = "\n\n\\section{" + got[1] + "}\n\n" + got[0]
                    elif "Problem Statement" not in got[1]:
                        inter += "\n\n\\section{" + got[1] + "}\n\n" + got[0].replace('\n', "\n\n")
                    else:
                        inter += got[0].replace('\n', "\n\n")
                    if got[2] and "Input" in got[1]:
                        input += '\n\n' + got[2]#.replace('\n', "\n\n")
                elif got[1] and "Sample" in got[1]:
                    if got[0]:
                        example_notes.append([got[1], got[0]])
                    if got[2]:
                        examples.append(got[2])
        # print(inter)

        # print(examples)
        assert len(examples) % 2 == 0
        example = ""
        for i in range(len(examples)):
            part = examples[i]
            part = self.remove_trailing(part)
            part = part.replace("\n", "\\newline\n") + '\n'
            if i % 2 == 0:
                part += "\t&\n"
            else:
                part += "\t\\\\ \\hline\n"
            example += part
        example = example.replace('#', "\#")

        input = self.remove_trailing(input)
        input = input.replace("\n\n", "\n")
        input = input.replace("\n", "\\newline\n")
        inter = inter.replace("\n\n\n", "\n\n")

        # print(example_notes)
        notes = "\\section{Notes}\n\n\\begin{itemize}\n"
        for part in example_notes:
            if not part[0] or not part[1]:
                continue
            for text in ["Input", "Output"]:
                part[0] = part[0].replace(text + " ", "")
            part[0] = self.remove_trailing(part[0])
            notes += "\n\\item " + part[0] + ":\n" + part[1] + "\n";
        notes += "\\end{itemize}"

        if len(example_notes) == 0:
            notes = ""

        latex = ""
        with open("template.tex", "r") as temp:
            latex = temp.read()

        latex = latex.replace("~statement~", inter)
        latex = latex.replace("~input~", input)
        latex = latex.replace("~output~", output)
        latex = latex.replace("~example~", example)
        latex = latex.replace("~notes~", notes)
        latex = latex.replace("~problemName~", self.problem_name[4:])
        # latex = latex.replace("~timeLimit~", self.time_limit)
        latex = latex.replace("~memoryLimit~", self.memory_limit)

        latex_file = open(self.doc_folder + "statement.tex", "w")
        latex_file.write(latex)
        latex_file.close()
        self.compile_statement(self.doc_folder, "statement.tex", "statement.pdf")
        latex_file = open(self.doc_folder + "statement.tex", "w")
        latex_file.write(latex.replace("logo", "doc/logo"))
        latex_file.close()
        for not_needed in ["aux", "log", "out"]:
            os.remove(self.doc_folder + "statement." + not_needed)

    def prepare_folders(self):
        print("Creating folders")
        self.main_folder = self.name_to_dir(self.problem_name) + '/'
        if os.path.exists(self.main_folder):
            shutil.rmtree(self.main_folder)
        if os.path.exists(self.main_folder[:-1] + ".zip"):
            os.remove(self.main_folder[:-1] + ".zip")
        self.doc_folder = self.main_folder + "doc/"
        self.prog_folder = self.main_folder + "prog/"
        self.in_folder = self.main_folder + "in/"
        self.out_folder = self.main_folder + "out/"
        self.create_dirs([self.main_folder, self.doc_folder, self.prog_folder, self.in_folder, self.out_folder])

    def create_config(self):
        # if not os.path.exists(self.main_folder + "Simfile"):
            # os.mknod(self.main_folder + "Simfile")
        simfile = open(self.main_folder + "Simfile", "w")
        simfile.write("name: " + self.problem_name[4:] + '\n')
        label = self.problem_name.lower()[4:7]
        print("- Label:", label)
        simfile.write("label: " + label + '\n')
        simfile.write("memory_limit: " + self.memory_limit + '\n')
        # simfile.write("global_time_limit: " + self.time_limit + '\n')
        simfile.close()

    def download_code(self, link):
        site = self.session.get(link).text
        bs = BeautifulSoup(site, "html5lib")
        #print(bs.prettify())
        for pre in bs.find_all("pre"):
            if pre.get('id') and pre.get('id') == "submission-code":
                return pre.text
        assert False

    def get_solutions(self):
        print("Downloading submissions")
        link = self.atcoder_link + "contests/" + self.round_name.lower() + "/submissions?f.Task=" + self.round_name.lower() + '_' + self.atcoder_label.lower() + "&f.LanguageName=C%2B%2B&f.Status={0}&f.User="
        for status in ["AC", "WA", "TLE"]:
            # print(link.format(status))
            site = self.session.get(link.format(status)).text
            bs = BeautifulSoup(site, "html5lib")

            if status == "AC":
                submit_limit = 5
                code_prefix = "ok"
            elif status == "WA":
                submit_limit = 3
                code_prefix = "wrong"
            elif status == "TLE":
                submit_limit = 2
                code_prefix = "slow"
            submit_cnt = 0

            for submit in bs.find_all('a'):
                if submit.text and submit.text == "Detail":
                    if submit_cnt == submit_limit:
                        break
                    submit_cnt += 1
                    l = submit.get("href")
                    filename = code_prefix + str(submit_cnt) + ".cpp"
                    print("- Downloading submission", filename)
                    code = self.download_code(self.atcoder_link[:-1] + l)
                    with open(self.prog_folder + filename, 'w') as file:
                        file.write("// This code should get " + status + " verdict\n")
                        file.write("// Autogenerated sim package by atcoder-sim\n")
                        file.write(code)

    def copy_download_script(self, link):
        path = self.main_folder + 'download_tests.py'
        shutil.copyfile("download_tests.py", path)
        with open(path, 'r') as f:
            s = f.read()
            s = s.replace('~link~', link)
        with open(path, 'w') as f:
            f.write(s)

    def sipzip(self):
        print("Zipping all")
        if os.path.exists("tmp"):
            shutil.rmtree("tmp")
        self.create_dirs(["tmp"])
        subprocess.call(["mv " + self.main_folder + " tmp/" + self.main_folder],
                shell=True, stdout=self.logfile, stderr=self.logfile)
        shutil.make_archive(self.main_folder[:-1], "zip", "tmp")
        subprocess.call(["mv tmp/" + self.main_folder + " " + self.main_folder],
                shell=True, stdout=self.logfile, stderr=self.logfile)
        shutil.rmtree("tmp")

    def __init__(self, round, problem, dropbox_link):
        self.round_name = round
        self.atcoder_label = problem
        problem_link = self.atcoder_link + "contests/" + round.lower() + "/tasks/" + round.lower() + "_" + problem.lower()
        print("Problem link:", problem_link)

        print("Downloading problem page")
        self.session = requests.Session()
        site = self.session.get(problem_link).text
        bs = BeautifulSoup(site, "html5lib")

        self.get_problem_info(bs)
        self.prepare_folders()
        self.create_statement(bs)
        self.create_config()
        self.get_solutions()
        self.copy_download_script(dropbox_link)
    
Paczkarka(sys.argv[1], sys.argv[2], sys.argv[3])
