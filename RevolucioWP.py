# -*- coding: utf-8 -*-

import os

from includes.wiki import get_wiki
from includes.wiki_tasks import wiki_task, _safe_log_exc
from config import ver

from pywikibot.comms.eventstreams import EventStreams

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
            if change.get("namespace") != 0:
                continue
            if change.get("type") not in ("edit", "new"):
                continue
        
            page_name = change.get("title")
            user = change.get("user")
            comment = change.get("comment")
            diff_url = change.get("meta", {}).get("uri")
        
            print(f"[{change.get('type')}] {page_name} — {user}")
            if comment:
                print(f"  ↳ {comment}")
            if diff_url:
                print(f"  ↳ {diff_url}")
        
            page = task.site.page(page_name)
        
            if page.special or not page.exists():
                continue
        
            print("Page : " + page_name)
    
            is_revert = any(tag in change.get("tags", []) for tag in ("mw-undo", "mw-rollback", "mw-manual-revert"))
    
            if not is_revert and not task.site.config.get("disable_vandalism", False):
                task.check_vandalism(page)
                print(f"Score de vandalisme : {task.vandalism_score}")
    
            if not is_revert and not task.site.config.get("disable_ai", False):
                task.check_vandalism_ai(page)
                print(f"Probabilité de vandalisme (IA) : {task.proba_ai} %")
                print(f"Analyse (IA) : {task.summary_ai}")
        except Exception:
            _safe_log_exc()

if __name__ == "__main__":
    main()