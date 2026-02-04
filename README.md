# RevolucioBot

Bot MediaWiki/Pywikibot destiné principalement à la maintenance des wikis MediaWiki.
Il est notamment destiné à repérer (via expressions rationnelles)
et traiter certains contenus, avec possibilité d'intégration via
**webhooks** et/ou d'assistance **IA** (LLM).

> Code partiellement généré ou restructuré avec ChatGPT.\
> Les fichiers d'expressions rationnelles sont adaptés de la
> configuration de Salebot :
> https://fr.wikipedia.org/wiki/Utilisateur:Salebot/Config\
> **Licence : GPLv3**

------------------------------------------------------------------------

## 🚀 Fonctionnalités

-   Détection de motifs via **expressions rationnelles (regex)**\
-   Connexion à un ou plusieurs wikis avec **Pywikibot**\
-   Support des **BotPasswords** MediaWiki\
-   Envoi de notifications via **webhooks HTTP**\
-   Intégration optionnelle d'un **modèle IA (LLM)**
-   Diverses autres fonctionnalités (suppression catégories inexistantes, corrections redirections, etc. adaptées à chaque wiki si besoin)

------------------------------------------------------------------------

## 🧰 Prérequis

-   Python 3.10+ recommandé\
-   Compte bot avec BotPasswords activés\
-   Accès aux variables d'environnement pour stocker les secrets

------------------------------------------------------------------------

## 📦 Installation

``` bash
git clone git@github.com:SkyGenProg/RevolucioBot.git
cd RevolucioBot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

------------------------------------------------------------------------

## ⚙️ Configuration

Définir les variables nécessaires (webhooks, clé API IA, mots de passe, modèle, etc., voir config.py et user-password.py).

------------------------------------------------------------------------

## ▶️ Lancer le bot

``` bash
python Revolucio.py
```

------------------------------------------------------------------------

## ▶️ Lancer le bot (sur les wikis ayant un flux de RC en direct)

``` bash
python RevolucioDirect.py
```

------------------------------------------------------------------------

## 📜 Licence

GNU GPL v3
