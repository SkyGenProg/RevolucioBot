# -*- coding: utf-8 -*-

import argparse, os, logging, threading

from includes.wiki import *
from includes.wiki_tasks import *
from config import *

logging.basicConfig(filename="logs.log", encoding="utf-8", level=logging.DEBUG, format="%(asctime)s %(thread)d %(levelname)s:%(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

arg = argparse.ArgumentParser()
arg.add_argument("--start_task_day", action="count")
arg.add_argument("--ignore_task_month", action="count")
args = arg.parse_args()

if __name__ == "__main__":
    print("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    vikidiafr_site = get_wiki("vikidia", "fr", "RevolucioBot")
    vikidiaen_site = get_wiki("vikidia", "en", "RevolucioBot")
    dicoado_site = get_wiki("dicoado", "dicoado", "RevolucioBot")
    #nomwiki_site = get_wiki("nomwiki", "langue", "utilisateur")
    vikidiafr_task = wiki_task(vikidiafr_site, args.start_task_day, args.ignore_task_month)
    vikidiaen_task = wiki_task(vikidiaen_site, args.start_task_day, args.ignore_task_month)
    dicoado_task = wiki_task(dicoado_site, args.start_task_day, args.ignore_task_month)
    #nomwiki_task = wiki_task(nomwiki_site, args.start_task_day, args.ignore_task_month)
    threading.Thread(target=vikidiafr_task.execute).start()
    threading.Thread(target=vikidiaen_task.execute).start()
    threading.Thread(target=dicoado_task.execute).start()
    #threading.Thread(target=nomwiki_task.execute).start()
