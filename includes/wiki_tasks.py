# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators, textlib
import base64, datetime, json, logging, os, random, re, socket, traceback, time, urllib.request, urllib.error, urllib.parse, zlib
from config import *
from includes.wiki import *

vand_f = lambda x: 101.2391 + (5.57778 - 101.2391) / (1 + (x / 9.042732)**1.931107)

class wiki_task:
    def __init__(self, site):
        self.site = site

    def execute(self):
        wiki = self.site.family
        lang = self.site.lang
        lang_bot = self.site.lang_bot
        while True:
            try:
                pages_checked = [] #pages vérifiées (pour éviter de revérifier la page)
                #Mise en mémoire du mois
                open("tasks_time_month_" + wiki + "_" + lang + ".txt", "a").close()
                with open("tasks_time_month_" + wiki + "_" + lang + ".txt", "r") as tasks_time_file:
                    tasks_time = tasks_time_file.read()
                if datetime.datetime.now().strftime("%Y%m") not in tasks_time: #taches mensuelles
                    #spécifiques au Dico des Ados
                    if wiki == "dicoado":
                        for page_name in self.site.all_pages(ns=0):
                            page = self.site.page(page_name)
                            print("Page : " + str(page))
                            try:
                                if not page.isRedirectPage():
                                    page_text_old = page.text
                                    for i in range(1, 5):
                                        if i == 1:
                                            n = ""
                                        else:
                                            n = str(i)
                                        if "|ex" + n + "=" in page.text:
                                            try:
                                                page_text_split = page.text.split("|ex" + n + "=")
                                                if "=" in page_text_split[1]:
                                                    page_text_split2 = page_text_split[1].split("=")
                                                else:
                                                    page_text_split2 = page_text_split[1].split("}}")
                                                page_text_split2[0] = re.sub("(\s|[=#'])(?!'{3,})\b(" + re.escape(page_name) + ")(\w{0,})\b(?!'{3,})", r"'''\2\3'''", page_text_split2[0])
                                                page_text_split2[0] = re.sub('\B(?!{{\"\|)\"\b([^\"]*)\b\"(?!}})\B', r'{{"|\1}}', page_text_split2[0])
                                                page_text_split3 = [i for i in page_text_split2[0]]
                                                page_text_split3[0] = page_text_split3[0].upper()
                                                page_text_split2[0] = "".join(page_text_split3)
                                                page_text_split[1] = "=".join(page_text_split2)
                                                page.text = ("|ex" + n + "=").join(page_text_split)
                                            except Exception as e:
                                                print(e)
                                        if "|contr" + n + "=" in page.text:
                                            try:
                                                page_text_split = page.text.split("|contr" + n + "=")
                                                if "=" in page_text_split[1]:
                                                    page_text_split2 = page_text_split[1].split("=")
                                                else:
                                                    page_text_split2 = page_text_split[1].split("}}")
                                                page_text_split2[0] = page_text_split2[0].replace("[[", "").replace("]]", "")
                                                page_text_split[1] = "=".join(page_text_split2)
                                                page.text = ("|contr" + n + "=").join(page_text_split)
                                            except Exception as e:
                                                print(e)
                                        if "|syn" + n + "=" in page.text:
                                            try:
                                                page_text_split = page.text.split("|syn" + n + "=")
                                                if "=" in page_text_split[1]:
                                                    page_text_split2 = page_text_split[1].split("=")
                                                else:
                                                    page_text_split2 = page_text_split[1].split("}}")
                                                page_text_split2[0] = page_text_split2[0].replace("[[", "").replace("]]", "")
                                                page_text_split[1] = "=".join(page_text_split2)
                                                page.text = ("|syn" + n + "=").join(page_text_split)
                                            except Exception as e:
                                                print(e)
                                        if "|voir" + n + "=" in page.text:
                                            try:
                                                page_text_split = page.text.split("|voir" + n + "=")
                                                if "=" in page_text_split[1]:
                                                    page_text_split2 = page_text_split[1].split("=")
                                                else:
                                                    page_text_split2 = page_text_split[1].split("}}")
                                                page_text_split2[0] = page_text_split2[0].replace("[[", "").replace("]]", "")
                                                page_text_split[1] = "=".join(page_text_split2)
                                                page.text = ("|voir" + n + "=").join(page_text_split)
                                            except Exception as e:
                                                print(e)
                                        if "|def" + n + "=" in page.text:
                                            try:
                                                page_text_split = page.text.split("|def" + n + "=")
                                                if "=" in page_text_split[1]:
                                                    page_text_split2 = page_text_split[1].split("=")
                                                else:
                                                    page_text_split2 = page_text_split[1].split("}}")
                                                page_text_split3 = [i for i in page_text_split2[0]]
                                                page_text_split3[0] = page_text_split3[0].lower()
                                                page_text_split2[0] = "".join(page_text_split3)
                                                page_text_split2[0] = re.sub('\B(?!{{\"\|)\"\b([^\"]*)\b\"(?!}})\B', r'{{"|\1}}', page_text_split2[0])
                                                page_text_split[1] = "=".join(page_text_split2)
                                                page.text = ("|def" + n + "=").join(page_text_split)
                                            except Exception as e:
                                                print(e)
                                    if "|son=LL-Q150" in page.text:
                                        page.text = page.text.replace("|son=LL-Q150", "|prononciation=LL-Q150")
                                    if page.text != page_text_old:
                                        page.save("maintenance")
                            except Exception as e:
                                print(e)
                if datetime.datetime.utcnow().strftime("%Y%m") not in tasks_time: #taches mensuelles
                    #Nettoyage des PDDs d'IPs (créer Modèle:Avertissement effacé)
                    for page_name in self.site.all_pages(ns=3, start="1", end="A"):
                        print("Page : " + page_name)
                        if (page_name.count(".") == 3 or page_name.count(":") == 8):
                            user_talk = pywikibot.User(self.site.site, ":".join(page_name.split(":")[1:]))
                            if user_talk.isAnonymous():
                                page = self.site.page(page_name)
                                print("PDD d'IP")
                                if page.page_ns == 3 and ("=" in page.text or "averto" in page.text.lower()) and abs((datetime.datetime.utcnow() - page.editTime()).days) > 365:
                                    print("Suppression des avertissements de la page " + page_name)
                                    try:
                                        if lang_bot == "fr":
                                            page.put("{{Avertissement effacé|{{subst:#time: j F Y}}}}", "Anciens messages effacés")
                                        else:
                                            page.put("{{Warning cleared|{{subst:#time: j F Y}}}}", "Old messages cleared")
                                    except Exception as e:
                                        print("Erreur :")
                                        try:
                                            print(traceback.format_exc())
                                        except UnicodeError:
                                            pass
                                else:
                                    print("Pas d'avertissement à effacer")
                            else:
                                print("Pas une PDD d'IP")
                        else:
                            print("Pas une PDD d'IP")
                    with open("tasks_time_month_" + wiki + "_" + lang + ".txt", "w") as tasks_time_file:
                        tasks_time_file.write(datetime.datetime.utcnow().strftime("%Y%m"))


                #Mise en mémoire de l'heure
                open("tasks_time_hour_" + wiki + "_" + lang + ".txt", "a").close()
                with open("tasks_time_hour_" + wiki + "_" + lang + ".txt", "r") as tasks_time_file:
                    tasks_time = tasks_time_file.read()
                if datetime.datetime.utcnow().strftime("%Y%m%d%H") not in tasks_time:
                    #Taches réalisées une fois par heure
                    if int(datetime.datetime.utcnow().strftime("%H")) == 0:
                        time1hour = datetime.datetime.utcnow() - datetime.timedelta(hours = 24)
                    else:
                        time1hour = datetime.datetime.utcnow() - datetime.timedelta(hours = 1)
                    for page_name in self.site.rc_pages(timestamp=time1hour.strftime("%Y%m%d%H%M%S")):
                        #parcours des modifications récentes
                        if page_name in pages_checked: #passage des pages déjà vérifiées
                            continue
                        page = self.site.page(page_name)
                        if page.special or not page.exists(): #passage des pages spéciales ou inexistantes
                            continue
                        print("Page : " + str(page))
                        if page.isRedirectPage():
                            print("Correction de redirection sur la page " + str(page))
                            redirect = page.redirects() #Correction redirections
                        else:
                            #détection vandalismes
                            vandalism_revert = page.vandalism_revert()
                            if vandalism_revert < 0: #Webhook d'avertissement
                                if webhooks_url[wiki] != None:
                                    vand_prob = vand_f(abs(vandalism_revert))
                                    if vand_prob > 100:
                                        vand_prob = 100
                                    if vandalism_revert <= page.limit:
                                        if lang_bot == "fr":
                                            title = "Modification non-constructive révoquée sur " + lang + ":" + page_name
                                            description = "Cette modification a été détectée comme non-constructive"
                                        else:
                                            title = "Unconstructive edit reverted on " + lang + ":" + page_name
                                            description = "This edit has been detected as unconstructive"
                                        color = 13371938
                                    elif vandalism_revert <= page.limit2:
                                        if lang_bot == "fr":
                                            title = "Modification suspecte sur " + lang + ":" + page_name
                                            description = "Cette modification est probablement non-constructive"
                                        else:
                                            title = "Edit maybe unconstructive on " + lang + ":" + page_name
                                            description = "This edit is probably unconstructive"
                                        color = 12138760
                                    else:
                                        if lang_bot == "fr":
                                            title = "Modification à vérifier sur " + lang + ":" + page_name
                                            description = "Cette modification est peut-être non-constructive"
                                        else:
                                            title = "Edit to verify on " + lang + ":" + page_name
                                            description = "This edit is maybe unconstructive"
                                        color = 12161032
                                    if lang_bot == "fr":
                                        fields = [
                                                {
                                                  "name": "Score",
                                                  "value": str(vandalism_revert),
                                                  "inline": True
                                                },
                                                {
                                                  "name": "Probabilité qu'il s'agisse d'une modification non-constructive",
                                                  "value": str(round(vand_prob, 2)) + " %",
                                                  "inline": True
                                                }
                                            ]
                                    else:
                                        fields = [
                                                {
                                                  "name": "Score",
                                                  "value": str(vandalism_revert),
                                                  "inline": True
                                                },
                                                {
                                                  "name": "Probability it's an unconstructive edit",
                                                  "value": str(round(vand_prob, 2)) + " %",
                                                  "inline": True
                                                }
                                            ]
                                    discord_msg = {'embeds': [
                                                    {
                                                          'title': title,
                                                          'description': description,
                                                          'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                                          'author': {'name': page.contributor_name},
                                                          'color': color,
                                                          'fields': fields
                                                    }
                                                ]
                                            }
                                    request_site(webhooks_url[wiki], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
                                    if page.alert_request:
                                        if lang_bot == "fr":
                                            discord_msg = {'embeds': [
                                                        {
                                                              'title': "Demande de blocage de " + page.contributor_name,
                                                              'description': "Un vandale est à bloquer.",
                                                              'url': page.protocol + "//" + page.url + page.articlepath + page.alert_page,
                                                              'author': {'name': page.contributor_name},
                                                              'color': 16711680
                                                        }
                                                    ]
                                                }
                                        else:
                                            discord_msg = {'embeds': [
                                                        {
                                                              'title': "Request to block against " + page.contributor_name,
                                                              'description': "A vandal must be blocked.",
                                                              'url': page.protocol + "//" + page.url + page.articlepath + page.alert_page,
                                                              'author': {'name': page.contributor_name},
                                                              'color': 16711680
                                                        }
                                                    ]
                                                }
                                        request_site(webhooks_url[wiki], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
                            if page.namespace() == 0:
                                edit_replace = page.edit_replace() #Recherches-remplacements
                                print(str(edit_replace) + " recherche(s)-remplacement(s) sur la page " + str(page) + ".")
                            if int(datetime.datetime.utcnow().strftime("%H")) == 0:
                                print("Suppression des catégories inexistantes sur la page " + str(page))
                                del_categories_no_exists = page.del_categories_no_exists() #Suppression 
                                if del_categories_no_exists != []:
                                    print("Catégories retirées " + ", ".join(del_categories_no_exists))
                                else:
                                    print("Aucune catégorie à retirer.")
                            pages_checked.append(page_name)
                    if wiki == "dicoado":
                        #spécifiques aux Dico des Ados
                        #remise à 0 du BàS du Dico des Ados
                        bas = self.site.page("Dico:Bac à sable")
                        bas_zero = self.site.page("Dico:Bac à sable/Zéro")
                        if abs((datetime.datetime.utcnow() - bas.editTime()).seconds) > 3600 and bas.text != bas_zero.text:
                            print("Remise à zéro du bac à sable")
                            bas.put(bas_zero.text, "Remise à zéro du bac à sable")
                        for page_name in self.site.all_pages(ns=4, apprefix="Bac à sable/Test/"):
                            if page_name != "Dico:Bac à sable/Zéro":
                                bas_page = self.site.page(page_name)
                                if abs((datetime.datetime.utcnow() - bas_page.editTime()).seconds) > 7200 and "{{SI" not in bas_page.text:
                                    print("SI de " + page_name)
                                    bas_page.text = "{{SI|Remise à zéro du bac à sable}}\n" + bas_page.text
                                    bas_page.save("Remise à zéro du bac à sable")
##                    if lang_bot == "fr":
##                        cat_files_no_exists = self.site.category("Category:Pages avec des liens de fichiers brisés")
##                        for page_cat in cat_files_no_exists.get_pages(ns=0):
##                            print("Suppression des fichiers inexistantes sur la page " + page_cat)
##                            page_cat_get = self.site.page(page_cat)
##                            del_files_no_exists = page_cat_get.del_files_no_exists()
##                            if del_files_no_exists != []:
##                                print("Fichiers retirés " + ", ".join(del_files_no_exists))
##                            else:
##                                print("Aucun fichier à retirer.")
                    with open("tasks_time_hour_" + wiki + "_" + lang + ".txt", "w") as tasks_time_file:
                        tasks_time_file.write(datetime.datetime.utcnow().strftime("%Y%m%d%H"))
            except Exception as e:
                print("Erreur :")
                try:
                    print(traceback.format_exc())
                except UnicodeError:
                    pass
            time.sleep(60)
