# -*- coding: utf-8 -*-

import argparse, os

from includes.wiki import get_wiki
from includes.wiki_tasks import wiki_task, _safe_log_exc
from version import ver

from pywikibot.comms.eventstreams import EventStreams

arg = argparse.ArgumentParser()
arg.add_argument("--test")
args = arg.parse_args()

def ensure_workdir(dirname="files"):
    os.makedirs(dirname, exist_ok=True)
    os.chdir(dirname)

def main():
    print(f"Revolució {ver}")
    ensure_workdir()

    # Stream global "recentchange" (tous wikis), on filtre ensuite sur frwiki
    stream = EventStreams(streams="recentchange")
    site = get_wiki("wikipedia", "fr", "RevolucioBot")
    task = wiki_task(site, False, False, True)

    for change in stream:
        try:
            if change.get("wiki") != "frwiki":
                continue
            if change.get("bot"):
                continue
            if change.get("type") not in ("edit", "new"):
                continue

            page_name = change.get("title")
            page = task.site.page(page_name)
            if page.special or not page.exists():
                continue

            rights = page.contributor_rights()
            is_revert = page.is_revert()
            if not is_revert and "autoconfirmed" not in rights:
                if site.bot_stopped():
                    task.send_message_bot_stopped()
                    print("Le bot a été arrêté.")
                    break

                if not task.site.config.get("disable_vandalism", False):
                    print(f"Calcul du score de vandalisme sur {page_name}...")
                    task.check_vandalism(page, args.test)
                    print(f"Score de vandalisme : {task.vandalism_score}")

                if not task.site.config.get("disable_ai", False):
                    print(f"Calcul du score de vandalisme (IA) sur {page_name}...")
                    task.check_vandalism_ai(page, args.test)
                    print(f"Probabilité de vandalisme (IA) : {task.proba_ai} %")

        except Exception:
            _safe_log_exc()

if __name__ == "__main__":
    main()
