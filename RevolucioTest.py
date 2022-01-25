# -*- coding: utf-8 -*-

import os, threading

from includes.wiki import *
from includes.wiki_tasks import *
from config import *

logging.basicConfig(filename="logs.log", encoding="utf-8", level=logging.DEBUG, format="%(asctime)s %(thread)d %(levelname)s:%(message)s")
logging.getLogger().addHandler(logging.StreamHandler())

if __name__ == "__main__":
    print("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    localhost_site = get_wiki("localhost", "localhost", "RevolucioBot")
    localhost_task = wiki_task(localhost_site)
    threading.Thread(target=localhost_task.execute).start()
