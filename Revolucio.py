# -*- coding: utf-8 -*-

import os, threading

from includes.wiki import *
from includes.wiki_tasks import *
from includes.vikidia import *
from config import *

os.chdir("files")

if __name__ == "__main__":
    print("Revolució %s %s." % (ver, lang))
    #dicoado_site = get_wiki(user_wiki=user_bot, lang=lang, family="dicoado")
    vikidia_task = wiki_task(wikis[0], user_bot)
    #dicoado_task = wiki_task(site=dicoado_site, user_bot=user_bot)
    threading.Thread(target=vikidia_task.execute).start()
    #threading.Thread(target=dicoado_task.execute).start()
