# -*- coding: utf-8 -*-

import argparse
import logging
import os
import threading

from includes.wiki import get_wiki
from includes.wiki_tasks import wiki_task
from version import ver

logging.basicConfig(
    filename="logs.log",
    encoding="utf-8",
    level=logging.DEBUG,
    format="%(asctime)s %(thread)d %(levelname)s:%(message)s",
)
logging.getLogger().addHandler(logging.StreamHandler())

WIKIS = [
    ("vikidia", "fr", "RevolucioBot"),
    ("vikidia", "en", "RevolucioBot"),
    ("dicoado", "dicoado", "RevolucioBot"),
    # ("nomwiki", "langue", "utilisateur"),
]
#WIKIS = [
#    ("localhost", "localhost", "RevolucioBot")
#]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start_task_day", action="count")
    p.add_argument("--start_task_month", action="count")
    p.add_argument("--ignore_task_month", action="count")
    return p.parse_args()


def ensure_workdir(dirname="files"):
    os.makedirs(dirname, exist_ok=True)
    os.chdir(dirname)


def start_tasks(args):
    threads = []
    for family, lang, user in WIKIS:
        site = get_wiki(family, lang, user)
        task = wiki_task(site, args.start_task_day, args.start_task_month, args.ignore_task_month)
        t = threading.Thread(
            target=task.execute,
            name=f"task:{family}:{lang}",
            daemon=True,  # optionnel : le process s'arrête proprement
        )
        t.start()
        threads.append(t)

    # Optionnel : garder le main vivant (sinon daemon=True suffit)
    for t in threads:
        t.join()


def main():
    print(f"Revolució {ver}")
    args = parse_args()
    ensure_workdir()
    start_tasks(args)


if __name__ == "__main__":
    main()