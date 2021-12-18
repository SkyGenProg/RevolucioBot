# -*- coding: utf-8 -*-

import os, threading

from includes.wiki import *
from includes.wiki_tasks import *
from config import *

if __name__ == "__main__":
    print("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    vikidiafr_site = get_wiki("vikidia", "fr")
    dicoado_site = get_wiki("dicoado", "dicoado")
    #nomwiki_site = get_wiki("nomwiki", "langue")
    vikidiafr_task = wiki_task(vikidiafr_site)
    dicoado_task = wiki_task(dicoado_site)
    #nomwiki_task = wiki_task(nomwiki_site)
    threading.Thread(target=vikidiafr_task.execute).start()
    threading.Thread(target=dicoado_task.execute).start()
    #threading.Thread(target=nomwiki_task.execute).start()
