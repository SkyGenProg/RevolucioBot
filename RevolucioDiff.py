# -*- coding: utf-8 -*-

import argparse, os, pywikibot, difflib

from includes.wiki import get_wiki
from config import api_key, model
from version import ver
from mistralai import Mistral

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--wiki", required=True)
required_arg.add_argument("--lang", required=True)
arg.add_argument("--user")
required_arg.add_argument("--page", required=True)
required_arg.add_argument("--diff", required=True)
required_arg.add_argument("--oldid", required=True)
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
    page = site.page(args.page)
    vandalism_score = page.vandalism_score(int(args.diff), int(args.oldid))
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
    revision1 = page.get_revision(int(args.oldid))
    revision2 = page.get_revision(int(args.diff))
    diff = difflib.unified_diff((revision1["text"] or "").splitlines(), (revision2["text"] or "").splitlines())
    diff_text = "\n".join(diff)
    #pywikibot.output(diff)
    prompt = f"""Analyser la modification, indiquer la probabilité que ce soit du vandalisme en % et résumer en 3 mots maximum la pertinence de la modification.
Si la modification est une révocation de vandalisme, mettre la probabilité de vandalisme à 0 %.
Si la modification est une annonce de décès, ne pas considérer la modification comme un vandalisme.
Date : {page.latest_revision.timestamp}
Wiki : {page.url}
Page : {page.page_name}
Diff :
{diff_text}
Résumé de modification : {revision2.comment}
Format de réponse :
Analyse de la modification :
...
Probabilité de vandalisme : [probabilité] %
Résumé : [résumé en 3 mots maximum]"""
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
    pywikibot.output(chat_response.choices[0].message.content)
