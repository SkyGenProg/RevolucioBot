# -*- coding: utf-8 -*-

import argparse, getpass

user_bot = "RevolucioBot"

ver = "5.0.0"
release_date = "19/12/2021"

webhooks_url = {'vikidia': "REMOVED",
                'dicoado': None} #Ajouter les nouveaux wikis
headers = {
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0 Revolucio'
}
