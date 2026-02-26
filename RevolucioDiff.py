# -*- coding: utf-8 -*-

import argparse, os, pywikibot, difflib

from includes.wiki import get_wiki, prompt_ai
from includes.wiki_tasks import predict
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
arg.add_argument("--oldid")
arg.add_argument("--use_ai")
arg.add_argument("--use_local_ai")
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
    page.get_text_page_old(int(args.diff), int(args.oldid) if args.oldid is not None else None, total=None)
    vandalism_score = page.vandalism_score()
    detected = page.get_vandalism_report()
    pywikibot.output(detected)
    pywikibot.output("Score : " + str(vandalism_score))
    pywikibot.output("Revoqué : " + str(page.edit_reverted))
    pywikibot.output("Utilisateur révoqué précédemment : " + str(page.user_previous_reverted))
    pywikibot.output("Date : " + str(page.timestamp))
    revision1_text = page.text_page_oldid
    revision2_text = page.text_page_oldid2
    diff = difflib.unified_diff(revision2_text.splitlines(), revision1_text.splitlines())
    diff_text = "\n".join(diff)
    pywikibot.output("Diff :")
    pywikibot.output(diff_text)
    if args.use_ai:
        prompt = prompt_ai(args.lang, page.timestamp, page.url, page.page_name, diff_text, page.comment)
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
    if args.use_local_ai:
        os.chdir("..")
        prob = predict(
            model_dir=site.config.get("local_ai_model"),
            norm_json=site.config.get("num_feat_norm"),
            old=revision2_text,
            new=revision1_text,
            diff=diff_text
        )
        pywikibot.output(f"Probabilité de vandalisme (IA locale) : {prob*100} %.")