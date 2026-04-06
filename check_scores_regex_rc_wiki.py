# -*- coding: utf-8 -*-

import argparse, csv, os, sys
csv.field_size_limit(sys.maxsize)
from includes.wiki import revision_info, vandalism_score
from datetime import datetime, timedelta

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--wiki", required=True)
required_arg.add_argument("--lang", required=True)
required_arg.add_argument("--csv_file", required=True)
required_arg.add_argument("--score_detect", type=int, required=True)
args = arg.parse_args()

true_positives = []
true_negatives = []
false_positives = []
false_negatives = []

fam = args.wiki
lang = args.lang
score_detect = args.score_detect

with open(args.csv_file, newline='', encoding='utf-8') as f:
    total = sum(1 for _ in csv.DictReader(f)) - 1
    f.seek(0)
    reader = csv.DictReader(f)
    if(not os.path.exists("files")):
       os.mkdir("files")
    os.chdir("files")
    start_time = datetime.now()
    for i, row in enumerate(reader, 0):
        if i > 0 and i % 100 == 0:
            elapsed = datetime.now() - start_time
            speed = i / elapsed.total_seconds()
            remaining = timedelta(seconds=(total - i) / speed)
            print(f"Progression : {i+1}/{total} ({i/total:.1%})\r\nTemps écoulé : {elapsed}\r\nTemps restant estimé : {remaining}")
        old = row["old"]
        new = row["new"]
        commented = row["commented"].strip().lower() == "true"
        new_page = row["new_page"].strip().lower() == "true"
        namespace = int(row["namespace"])
        timestamp = datetime.strptime(row["date"], "%Y-%m-%dT%H:%M:%SZ")
        contributor_name = row["contributor_name"]
        timestamp_created = datetime.strptime(row["timestamp_created"], "%Y-%m-%dT%H:%M:%SZ")
        author = row["author"]
        revision = revision_info(new, old, commented, new_page, namespace, "redirect" in new.lower(), timestamp, contributor_name, timestamp_created, author)
        files = {
            "add_regex_ns_0": f"regex_vandalisms_0_{fam}_{lang}.txt",
            "add_regex_ns_0_no_ignore_case": f"regex_vandalisms_0_{fam}_{lang}_no_ignore_case.txt",
            "add_regex_ns_all": f"regex_vandalisms_all_{fam}_{lang}.txt",
            "add_regex_ns_all_no_ignore_case": f"regex_vandalisms_all_{fam}_{lang}_no_ignore_case.txt",
            "del_regex_ns_0": f"regex_vandalisms_del_0_{fam}_{lang}.txt",
            "del_regex_ns_0_no_comment": f"regex_vandalisms_del_0_{fam}_{lang}_no_comment.txt",
            "size": f"size_vandalisms_0_{fam}_{lang}.txt"
        }
        vand_score = vandalism_score(files, revision)
        score = vand_score.calculate()
        reverted = row["reverted"].strip().lower() == "true"
        row["score_algo"] = score
        
        # Faux-positif
        if score <= score_detect:
            if reverted:
                true_positives.append(row)
            else:
                false_positives.append(row)
        
        # Faux-négatif
        if score > score_detect:
            if reverted:
                false_negatives.append(row)
            else:
                true_negatives.append(row)

print(f"Nombre de faux-positifs (modifications constructives détectées comme non-constructives) : {len(false_positives)}")
print(f"Nombre de faux-négatifs (modifications non-constructives détectées comme constructives) : {len(false_negatives)}")
print(f"Nombre de vrai-positifs (modifications non-constructives détectées comme non-constructives) : {len(true_positives)}")
print(f"Nombre de vrai-négatifs (modifications constructives détectées comme constructives) : {len(true_negatives)}")

print("\nListe des faux-positifs :")
for fp in false_positives:
    print(
        f"- date={fp['date']}, wiki={fp['wiki']}, page={fp['page']}, "
        f"revid={fp['revid']}, score={fp['score_algo']}, reverted={fp['reverted']}"
    )
print("\nListe des faux-négatifs :")
for fn in false_negatives:
    print(
        f"- date={fn['date']}, wiki={fn['wiki']}, page={fn['page']}, "
        f"revid={fn['revid']}, score={fn['score_algo']}, reverted={fn['reverted']}"
    )