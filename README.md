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
-   Compte bot ou compte utilisateur avec BotPasswords activés\
-   Accès aux variables d'environnement pour stocker les secrets

------------------------------------------------------------------------

## 📦 Installation

``` bash
git clone <url-du-repo>
cd revoluciobot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

------------------------------------------------------------------------

## ⚙️ Configuration

### 1️⃣ Renommer les fichiers d'exemple

``` bash
cp config.py.example config.py
cp user-password.py.example user-password.py
```

### 2️⃣ Variables d'environnement

Définir les variables nécessaires (webhooks, clé API IA).

### 3️⃣ Identifiants bot

Configurer `user-password.py` avec vos identifiants BotPasswords
MediaWiki.

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

## 🔐 Sécurité

Ne jamais committer les fichiers contenant des secrets.

------------------------------------------------------------------------

## 📜 Licence

GNU GPL v3
