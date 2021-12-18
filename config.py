# -*- coding: utf-8 -*-

import argparse, getpass

user_bot = "RevolucioBot"
page_test = "User:" + user_bot + "/Test"

ver = "5.0.0"
release_date = "19/12/2021"

arg = argparse.ArgumentParser()
arg.add_argument("--test")
args = arg.parse_args()

if args.test:
    test = True
else:
    test = False
