# -*- coding: utf-8 -*-

import argparse, os, pywikibot

from includes.wiki import get_wiki
from config import ver

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--wiki", required=True)
required_arg.add_argument("--lang", required=True)
arg.add_argument("--user")
required_arg.add_argument("--page", required=True)
required_arg.add_argument("--diff")
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
    if args.diff is None:
        score_check_WP = page.check_WP()
        pywikibot.output("Probabilité de copie de Wikipédia de la page " + str(page) + " : " + str(round(score_check_WP/len(page.text.strip())*100, 2)) + " % (" + str(score_check_WP) + " octets en commun/" + str(len(page.text.strip())) + " octets))")
    else:
        score_check_WP = page.check_WP(diff=int(args.diff))
        pywikibot.output("Probabilité de copie de Wikipédia de la page " + str(page) + " : " + str(round(score_check_WP/len(page.getOldVersion(oldid = int(args.diff)).strip())*100, 2)) + " % (" + str(score_check_WP) + " octets en commun/" + str(len(page.getOldVersion(oldid = int(args.diff)).strip())) + " octets))")
