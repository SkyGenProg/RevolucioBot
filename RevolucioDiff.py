# -*- coding: utf-8 -*-

import argparse, os, logging

from includes.wiki import *
from includes.wiki_tasks import *
from config import *

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--wiki", required=True)
required_arg.add_argument("--lang", required=True)
arg.add_argument("--user")
required_arg.add_argument("--page", required=True)
required_arg.add_argument("--diff", required=True)
required_arg.add_argument("--oldid", required=True)
args = arg.parse_args()

if __name__ == "__main__":
    print("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    if args.user != None:
        site = get_wiki(args.wiki, args.lang, args.user)
    else:
        site = get_wiki(args.wiki, args.lang, "RevolucioBot")
    page = site.page(args.page)
    vandalism_score = page.vandalism_score(int(args.diff), int(args.oldid))
    detected = ""
    for vandalism_score_detect in page.vandalism_score_detect:
        if vandalism_score_detect[0] == "add_regex":
            detected += str(vandalism_score_detect[1]) + " - + " + str(vandalism_score_detect[2].group()) + "\n"
        elif vandalism_score_detect[0] == "size":
            detected += str(vandalism_score_detect[1]) + " - size = " + str(page.size) + " < " + vandalism_score_detect[2] + "\n"
        elif vandalism_score_detect[0] == "diff":
            if int(vandalism_score_detect[2]) > 0:
                detected += str(vandalism_score_detect[1]) + " - diff > " + vandalism_score_detect[2] + "\n"
            else:
                detected += str(vandalism_score_detect[1]) + " - diff < " + vandalism_score_detect[2] + "\n"
        elif vandalism_score_detect[0] == "del_regex":
            detected += str(vandalism_score_detect[1]) + " - - " + str(vandalism_score_detect[2].group()) + "\n"
        else:
            detected += str(vandalism_score_detect[1]) + " - + " + str(vandalism_score_detect[2].group()) + "\n"
    print(detected)
    print("Score : " + str(vandalism_score))
