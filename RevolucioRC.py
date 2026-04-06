# -*- coding: utf-8 -*-

import argparse, os, pywikibot, difflib, csv, traceback, time
from urllib.parse import quote
from includes.wiki import get_wiki
from version import ver
from datetime import datetime, timedelta
from urllib.error import HTTPError

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--wiki", required=True)
required_arg.add_argument("--lang", required=True)
arg.add_argument("--user")
required_arg.add_argument("--limit", type=int, required=True)
args = arg.parse_args()

if __name__ == "__main__":
    pywikibot.output("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    if args.user != None:
        site = get_wiki(args.wiki, args.lang, args.user)
    else:
        site = get_wiki(args.wiki, args.lang, "RevolucioBot")
    site.get_trusted()
    timestamp = str((datetime.now() - timedelta(seconds=args.limit)).timestamp())
    site.rc_pages(timestamp=timestamp, rctoponly=False)
    output_file = f"rc_wiki_{args.wiki}_{args.lang}.csv"
    csv_file = open(output_file, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow([
        "date",
        "wiki",
        "contributor_name",
        "page",
        "namespace",
        "revid",
        "old_revid",
        "old",
        "new",
        "diff",
        "comment",
        "commented",
        "new_page",
        "timestamp_created",
        "author",
        "diff_url",
        "reverted"
    ])
    total = len(site.diffs_rc)
    start_time = datetime.now()
    for i, page_info in enumerate(site.diffs_rc, 0):
        if i > 0 and i % 100 == 0:
            elapsed = datetime.now() - start_time
            speed = i / elapsed.total_seconds()
            remaining = timedelta(seconds=(total - i) / speed)
            pywikibot.output(f"Progression : {i+1}/{total} ({i/total:.1%})\r\nTemps écoulé : {elapsed}\r\nTemps restant estimé : {remaining}")
        status_ok = False
        while not status_ok:
            try:
                page_name = page_info["title"]
                user = page_info["user"]
                ignored = False
                pages_ignore = site.config.get("ignore")
                if pages_ignore is not None:
                    for page_ignore in pages_ignore:
                        if page_ignore in page_name:
                            ignored = True
                            break
                    if ignored:
                        status_ok = True
                        continue
                if ignored or user in site.trusted:
                    status_ok = True
                    continue
                user_rights = site.rights(user)
                if "autoconfirmed" in user_rights:
                    status_ok = True
                    continue
                page = site.page(page_name)
                if page.special or not page.exists() or page.isRedirectPage():
                    status_ok = True
                    continue
                pywikibot.output("Page : " + page_name)
                page.get_text_page_old(int(page_info["revid"]), int(page_info["old_revid"]) if int(page_info["old_revid"]) > 0 else None, endtime=timestamp)
                revision1_text = page.text_page_oldid
                revision2_text = page.text_page_oldid2
                diff = difflib.unified_diff(revision2_text.splitlines(), revision1_text.splitlines())
                diff_text = "\n".join(diff)
                diff_comment = page.comment
                diff_url = (
                    f"{site.url}/w/index.php?"
                    f"title={quote(page.page_name.replace(' ', '_'))}"
                    f"&diff={page_info['revid']}"
                    f"&oldid={page_info['old_revid']}"
                )
                writer.writerow([
                    page.timestamp.isoformat(),
                    f"{args.lang}.{args.wiki}",
                    page.contributor_name,
                    page.page_name,
                    int(page.page_ns),
                    page_info["revid"],
                    page_info["old_revid"],
                    page.text_page_oldid2,
                    page.text_page_oldid,
                    diff_text,
                    diff_comment,
                    page.commented,
                    page.new_page,
                    page.timestamp_created.isoformat(),
                    page.author,
                    diff_url,
                    page.edit_reverted
                ])
                status_ok = True
            except HTTPError:
                pywikibot.error(traceback.format_exc())
                pywikibot.error("Erreur de connexion. Nouvel essai dans 10 secondes...")
                time.sleep(10)
            except Exception:
                pywikibot.error(traceback.format_exc())
                status_ok = True
    csv_file.flush()
    csv_file.close()