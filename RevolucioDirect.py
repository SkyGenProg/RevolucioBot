# -*- coding: utf-8 -*-

import argparse, os

from includes.wiki import get_wiki
from includes.wiki_tasks import wiki_task
from config import WIKIS
from version import ver
import threading

arg = argparse.ArgumentParser()
arg.add_argument("--test")
args = arg.parse_args()

def ensure_workdir(dirname="files"):
    os.makedirs(dirname, exist_ok=True)
    os.chdir(dirname)

def main():
    print(f"Revolució {ver}")
    ensure_workdir()
    threads = []
    for family, lang, user, direct in WIKIS:
        if direct:
            # Stream global "recentchange" (tous wikis), on filtre ensuite sur frwiki
            site = get_wiki(family, lang, user)
            task = wiki_task(site, False, False, True, args.test)
            t = threading.Thread(
                target=task.execute_direct,
                name=f"task:{family}:{lang}",
                daemon=True,  # optionnel : le process s'arrête proprement
            )
            t.start()
            threads.append(t)

    # Optionnel : garder le main vivant (sinon daemon=True suffit)
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
