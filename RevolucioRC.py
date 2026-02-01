# -*- coding: utf-8 -*-

import argparse, os, pywikibot, difflib, csv, traceback
from urllib.parse import quote
from includes.wiki import get_wiki, prompt_ai
from config import api_key, model
from version import ver
from mistralai import Mistral
from datetime import datetime, timedelta

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--wiki", required=True)
required_arg.add_argument("--lang", required=True)
arg.add_argument("--user")
required_arg.add_argument("--limit", required=True)
args = arg.parse_args()

client = Mistral(api_key=api_key)

if __name__ == "__main__":
    pywikibot.output("Revolució %s" % ver)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    if args.user != None:
        site = get_wiki(args.wiki, args.lang, args.user)
    else:
        site = get_wiki(args.wiki, args.lang, "RevolucioBot")
    site.rc_pages(timestamp=str((datetime.now() - timedelta(seconds=int(args.limit))).timestamp()))
    output_file = "ia_wiki_results.csv"
    file_exists = os.path.isfile(output_file)
    
    csv_file = open(output_file, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    
    if not file_exists:
        writer.writerow([
            "date",
            "wiki",
            "page",
            "revid",
            "old_revid",
            "diff_url",
            "score_algo",
            "probabilite_vandalisme"
        ])
    for page_info in site.diffs_rc:
        try:
            page_name = page_info["title"]
            page = site.page(page_name)
    
            if page.special or not page.exists() or page.isRedirectPage():
                continue
    
            pywikibot.output("Page : " + page_name)
    
            page = site.page(page_name)
            vandalism_score = page.vandalism_score(int(page_info["revid"]), int(page_info["old_revid"]))
            detected = ""
            for vandalism_score_detect in page.vandalism_score_detect:
                if vandalism_score_detect[0] == "add_regex":
                    detected += str(vandalism_score_detect[1]) + " - + " + str(vandalism_score_detect[2].group()) + "\n"
                elif vandalism_score_detect[0] == "size":
                    detected += str(vandalism_score_detect[1]) + " - size = " + str(page.size) + " < " + vandalism_score_detect[2] + "\n"
                elif vandalism_score_detect[0] == "diff":
                    if int(vandalism_score_detect[2]) > 0:
                        detected += str(vandalism_score_detect[1]) + " - diff > " + vandalism_score_detect[2] + "\n"
                    else:
                        detected += str(vandalism_score_detect[1]) + " - diff < " + vandalism_score_detect[2] + "\n"
                elif vandalism_score_detect[0] == "del_regex":
                    detected += str(vandalism_score_detect[1]) + " - - " + str(vandalism_score_detect[2].group()) + "\n"
                else:
                    detected += str(vandalism_score_detect[1]) + " - + " + str(vandalism_score_detect[2].group()) + "\n"
            pywikibot.output(detected)
            pywikibot.output("Score : " + str(vandalism_score))
            #pywikibot.output("Diff : ")
            revision1 = page.get_revision(int(page_info["old_revid"]))
            revision2 = page.get_revision(int(page_info["revid"]))
            diff = difflib.unified_diff((revision1["text"] or "").splitlines(), (revision2["text"] or "").splitlines())
            diff_text = "\n".join(diff)
            #pywikibot.output(diff)
            prompt = prompt_ai(args.lang, page.url, page.page_name, diff_text, revision2.comment)
            pywikibot.output("Prompt :")
            pywikibot.output(prompt)
            pywikibot.output("Analyse de l'IA : ")
            chat_response = client.chat.complete(
                model = model,
                messages = [
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ]
            )
            ia_text = chat_response.choices[0].message.content
            pywikibot.output(ia_text)
    
            diff_url = (
                f"{site.url}/w/index.php?"
                f"title={quote(page.page_name.replace(' ', '_'))}"
                f"&diff={page_info['revid']}"
                f"&oldid={page_info['old_revid']}"
            )

            probabilite = ""
            
            for line in ia_text.splitlines():
                if "Probabilité de vandalisme" in line:
                    probabilite = line.split(":")[-1].strip()
            writer.writerow([
                page.latest_revision.timestamp.isoformat(),
                f"{args.lang}.{args.wiki}",
                page.page_name,
                page_info["revid"],
                page_info["old_revid"],
                diff_url,
                vandalism_score,
                probabilite
            ])
        except Exception:
            pywikibot.error(traceback.format_exc())
    csv_file.flush()
    csv_file.close()
