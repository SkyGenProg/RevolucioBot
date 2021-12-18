# -*- coding: utf-8 -*-

import argparse, getpass

wikis = ["fr.vikidia.org", "dicoado.org:443"]
user_bot = "RevolucioBot"
page_test = "Utilisateur:" + user_bot + "/Test"

ver = "5.0.0"
lang = "fr"
release_date = "19/12/2021"

arg = argparse.ArgumentParser()
arg.add_argument("--test")
args = arg.parse_args()

if args.test:
    test = True
else:
    test = False
