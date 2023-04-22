# -*- coding: utf-8 -*-

import argparse, os, logging, threading

from includes.wiki import *
from includes.wiki_tasks import *
from config import *

logging.basicConfig(filename="logs.log", encoding="utf-8", level=logging.DEBUG, format="%(asctime)s %(thread)d %(levelname)s:%(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

arg = argparse.ArgumentParser()
arg.add_argument("--start_task_day")
args = arg.parse_args()

if __name__ == "__main__":
    print("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    if args.start_task_day != None:
        start_task_day = True
    else:
        start_task_day = False
    vikidiafr_site = get_wiki("vikidia", "fr", "RevolucioBot")
    vikidiaen_site = get_wiki("vikidia", "en", "RevolucioBot")
    dicoado_site = get_wiki("dicoado", "dicoado", "RevolucioBot")
    #nomwiki_site = get_wiki("nomwiki", "langue", "utilisateur")
    vikidiafr_task = wiki_task(vikidiafr_site, start_task_day)
    vikidiaen_task = wiki_task(vikidiaen_site, start_task_day)
    dicoado_task = wiki_task(dicoado_site, start_task_day)
    #nomwiki_task = wiki_task(nomwiki_site, start_task_day)
    threading.Thread(target=vikidiafr_task.execute).start()
    threading.Thread(target=vikidiaen_task.execute).start()
    threading.Thread(target=dicoado_task.execute).start()
    #threading.Thread(target=nomwiki_task.execute).start()
