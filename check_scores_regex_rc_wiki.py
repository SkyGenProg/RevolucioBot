# -*- coding: utf-8 -*-

import argparse, csv, sys
csv.field_size_limit(sys.maxsize)

arg = argparse.ArgumentParser()
required_arg = arg.add_argument_group("required arguments")
required_arg.add_argument("--csv_file", required=True)
args = arg.parse_args()

true_positives = []
true_negatives = []
false_positives = []
false_negatives = []

with open(args.csv_file, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        score = float(row["score_algo"])
        reverted = row["reverted"].strip().lower() == "true"
        
        # Faux-positif : score <= -20 et reverted = False
        if score <= -20:
            if reverted:
                true_positives.append(row)
            else:
                false_positives.append(row)
        
        # Faux-négatif : score > -20 et reverted = True
        if score > -20:
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