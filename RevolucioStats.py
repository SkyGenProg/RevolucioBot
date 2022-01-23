# -*- coding: utf-8 -*-

import csv, os, time

from includes.wiki import *
from includes.wiki_tasks import *
from config import *

if __name__ == "__main__":
    print("Revolució Stats %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    site = get_wiki("vikidia", "fr", "RevolucioBot")
    scores = site.get_scores(hours=24)
    print(scores)
    scores_n = {}
    scores_n_reverted = {}
    for diff in scores:
        if "score" in scores[diff]:
            if scores[diff]["score"] not in scores_n:
                scores_n[scores[diff]["score"]] = 1
                scores_n_reverted[scores[diff]["score"]] = 0
            else:
                scores_n[scores[diff]["score"]] += 1
            if scores[diff]["reverted"]:
                scores_n_reverted[scores[diff]["score"]] += 1
    print(scores_n)
    print(scores_n_reverted)
    scores_n_prop_modifs = []
    for score_n in scores_n:
        scores_n_prop_modifs.append([score_n, scores_n_reverted[score_n]/scores_n[score_n]])
    print(scores_n_prop_modifs)
    with open("vand.csv", "w") as file:
        writer = csv.writer(file)
        for line in scores_n_prop_modifs:
            writer.writerow(line)
