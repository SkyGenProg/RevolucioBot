# -*- coding: utf-8 -*-

import json, os, re, urllib.request, urllib.error, urllib.parse, zlib
from config import *
from includes.wiki import *

class get_vikidia(get_wiki):
    def __init__(self, lang_vd="fr", user_wiki=user_bot):
        get_wiki.__init__(self, lang_vd + ".vikidia.org", user_wiki)

    def page(self, page_wiki):
        return get_page_vikidia(self, page_wiki)

class get_page_vikidia(get_page):
    def __init__(self, source, title):
        get_page.__init__(self, source, title)

vand_f = lambda x: 101.2391 + (5.57778 - 101.2391) / (1 + (x / 9.042732)**1.931107)
