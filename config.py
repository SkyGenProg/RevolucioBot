# -*- coding: utf-8 -*-

import os

ver = "6.2.1"
release_date = "04/10/2025"

webhooks_url = {'localhost': "REMOVED",
                'vikidia': "REMOVED",
                'dicoado': "REMOVED"} #Ajouter les nouveaux wikis

webhooks_url_ai = {'localhost': "REMOVED",
                'vikidia': "REMOVED",
                'dicoado': "REMOVED"} #Ajouter les nouveaux wikis

headers = {
    'content-type': 'application/json',
    'user-agent': 'Mozilla/5.0 Revolucio'
}

api_key = os.environ["MISTRAL_API_KEY"]
model = "mistral-large-latest"
