# -*- coding: utf-8 -*-

try:
    import pywikibot
    from pywikibot import pagegenerators, textlib
    no_pywikibot = False
except ImportError:
    no_pywikibot = True
    input("Pywikibot doit être installé sur votre PC ou serveur pour exécuter ce bot, ou il est possible que vous n'avez pas installé ou utilisé Pywikibot correctement.")

import base64, datetime, json, logging, os, random, re, socket, time, urllib.request, urllib.error, urllib.parse, zlib
from config import *
from includes.wiki import *
from includes.vikidia import *

class wiki_task:
    def __init__(self, url=None, user_bot=None, site=None):
        if site is None:
            if "vikidia" in url:
                self.site = get_vikidia(url.split(".")[0], user_bot)
            else:
                self.site = get_wiki(url, user_bot)
        else:
            self.site = site

    def execute(self):
        wiki = self.site.url
        while True:
            try:
                pages_checked = []
                open("tasks_time_month_" + wiki + ".txt", "a").close()
                with open("tasks_time_month_" + wiki + ".txt", "r") as tasks_time_file:
                    tasks_time = tasks_time_file.read()
                if datetime.datetime.now().strftime("%Y%m") not in tasks_time:
                    if wiki == "dicoado.org:443":
                        for page_name in self.site.all_pages(ns=0):
                            page = self.site.page(page_name)
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
                    if wiki == "fr.vikidia.org":
                        for page_name in self.site.all_pages(ns=3, start="1", end="A"):
                            if (page_name.count(".") == 3 or page_name.count(":") == 8):
                                user_talk = pywikibot.User(self.site.site, ":".join(page_name.split(":")[1:]))
                                if user_talk.isAnonymous():
                                    page = self.site.page(page_name)
                                    if page.page_ns == 3 and ("=" in page.text or "averto" in page.text.lower()) and abs((datetime.datetime.utcnow() - page.editTime()).days) > 365:
                                        print("Suppression des avertissements de la page " + page_name)
                                        try:
                                            page.put("{{Avertissement effacé|{{subst:#time: j F Y}}}}", "Avertissement effacé")
                                        except Exception as e:
                                            print("Erreur :")
                                            try:
                                                print(e)
                                            except UnicodeError:
                                                pass
                    with open("tasks_time_month_" + wiki + ".txt", "w") as tasks_time_file:
                        tasks_time_file.write(datetime.datetime.now().strftime("%Y%m"))
                open("tasks_time_hour_" + wiki + ".txt", "a").close()
                with open("tasks_time_hour_" + wiki + ".txt", "r") as tasks_time_file:
                    tasks_time = tasks_time_file.read()
                if datetime.datetime.now().strftime("%Y%m%d%H") not in tasks_time:
                    #print(self.site.rc_list(timestamp=(datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y%m%d%H%M%S")))
                    if wiki == "fr.vikidia.org":
                        talks_update = self.site.talks_update()
                    if int(datetime.datetime.now().strftime("%H")) == 0:
                        time1hour = datetime.datetime.now() - datetime.timedelta(hours = 24)
                    else:
                        time1hour = datetime.datetime.now() - datetime.timedelta(hours = 3)
                    for page_name in self.site.rc_pages(timestamp=time1hour.strftime("%Y%m%d%H%M%S")):
                        if page_name in pages_checked:
                            continue
                        page = self.site.page(page_name)
                        if page.special or not page.exists():
                            continue
                        print("Page : " + str(page))
                        if page.isRedirectPage():
                            if wiki != "dicoado.org:443":
                                print("Correction de redirection sur la page " + str(page))
                                redirect = page.redirects()
                        else:
                            vandalism_revert = page.vandalism_revert()
                            if wiki == "dicoado.org:443":
                                page.alert_page = "Project:Alerte/" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                            else:
                                if vandalism_revert <= page.limit2:
                                    print("Modification suspecte détectée.")
                                if page.namespace() == 0:
                                    edit_replace = page.edit_replace()
                                    if edit_replace:
                                        with open("replace1.txt", "r") as replace1:
                                            with open("replace2.txt", "r") as replace2:
                                                print(replace1.read() + " remplacé par " + replace2.read() + " sur la page " + str(page) + ".")
                                if int(datetime.datetime.now().strftime("%H")) == 0:
                                    print("Suppression des catégories inexistantes sur la page " + str(page))
                                    del_categories_no_exists = page.del_categories_no_exists()
                                    if del_categories_no_exists != []:
                                        print("Catégories retirées " + ", ".join(del_categories_no_exists))
                                    else:
                                        print("Aucune catégorie à retirer.")
                            pages_checked.append(page_name)
                    if wiki == "dicoado.org:443":
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
##                    if lang == "fr":
##                        cat_files_no_exists = self.site.category("Category:Pages avec des liens de fichiers brisés")
##                        for page_cat in cat_files_no_exists.get_pages(ns=0):
##                            print("Suppression des fichiers inexistantes sur la page " + page_cat)
##                            page_cat_get = self.site.page(page_cat)
##                            del_files_no_exists = page_cat_get.del_files_no_exists()
##                            if del_files_no_exists != []:
##                                print("Fichiers retirés " + ", ".join(del_files_no_exists))
##                            else:
##                                print("Aucun fichier à retirer.")
                    with open("tasks_time_hour_" + wiki + ".txt", "w") as tasks_time_file:
                        tasks_time_file.write(datetime.datetime.now().strftime("%Y%m%d%H"))
                time.sleep(60)
            except Exception as e:
                print("Erreur :")
                try:
                    print(e)
                except UnicodeError:
                    pass
