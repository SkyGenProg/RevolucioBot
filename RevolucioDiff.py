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
    vandalism_score = page.vandalism_score(int(args.diff), int(args.oldid) if args.oldid is not None else None)
    detected = page.get_vandalism_report()
    pywikibot.output(detected)
    pywikibot.output("Score : " + str(vandalism_score))
    pywikibot.output("Révoqué précédemment : " + str(page.user_previous_reverted))
    if args.use_ai:
        revision1 = page.get_revision(int(args.diff))
        revision2 = page.get_revision(page.oldid)
        diff = difflib.unified_diff((revision2["text"] or "").splitlines(), (revision1["text"] or "").splitlines())
        diff_text = "\n".join(diff)
        prompt = prompt_ai(args.lang, revision1.timestamp, page.url, page.page_name, diff_text, revision1.comment)
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
        revision1 = page.get_revision(int(args.diff))
        revision2 = page.get_revision(page.oldid)
        diff = difflib.unified_diff((revision2["text"] or "").splitlines(), (revision1["text"] or "").splitlines())
        diff_text = "\n".join(diff)
        prob = predict(
            model_dir=site.config.get("local_ai_model"),
            norm_json=site.config.get("num_feat_norm"),
            old=revision2["text"],
            new=revision1["text"],
            diff=diff_text
        )
        pywikibot.output(f"Probabilité de vandalisme (IA locale) : {prob}")