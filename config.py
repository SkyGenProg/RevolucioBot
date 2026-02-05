# -*- coding: utf-8 -*-

import os

WIKIS = [
    ("vikidia", "fr", "RevolucioBot", False),
    ("vikidia", "en", "RevolucioBot", False),
    ("dicoado", "dicoado", "RevolucioBot", False),
    ("wikipedia", "fr", "RevolucioBot", True),
]
#WIKIS = [
#    ("localhost", "localhost", "RevolucioBot", False)
#]

webhooks_url = {'support': os.getenv("revolucio_webhook_url_support"),
                'localhost': os.getenv("revolucio_webhook_url_localhost"),
                'vikidia': os.getenv("revolucio_webhook_url_vikidia"),
                'dicoado': os.getenv("revolucio_webhook_url_dicoado"),
                'wikipedia': os.getenv("revolucio_webhook_url_wikipedia}

webhooks_url_ai = {'localhost': os.getenv("revolucio_webhook_url_ai_localhost"),
                   'vikidia': os.getenv("revolucio_webhook_url_ai_vikidia"),
                   'dicoado': os.getenv("revolucio_webhook_url_ai_dicoado"),
                   'wikipedia': os.getenv("revolucio_webhook_url_ai_wikipedia")}

headers = {
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 Revolucio",
}

api_key = os.getenv("revolucio_api_key")
model = os.getenv("revolucio_model")