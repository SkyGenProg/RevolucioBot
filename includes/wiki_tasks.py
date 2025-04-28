# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators, textlib
import base64, datetime, json, os, random, re, socket, time, traceback, urllib.request, urllib.error, urllib.parse, zlib
from config import *
from includes.wiki import *
from scipy.optimize import curve_fit
from mistralai import Mistral

client = Mistral(api_key=api_key)

def curve(x, a, b, c, d):
    return d+(a-d)/(1+(x/c)**b)

vand_f = lambda x: curve(x, 5.57778, 1.931107, 9.042732, 101.2391)

class wiki_task:
    def __init__(self, site, start_task_day=False, start_task_month=False, ignore_task_month=False):
        self.site = site
        self.start_task_day = start_task_day
        self.start_task_month = start_task_month and not ignore_task_month
        self.ignore_task_month = ignore_task_month
        self.site.get_trusted() #récupération des utilisateurs ignorés par le bot

    def task_every_month(self):
        pywikibot.output("Tâches mensuelles (" + self.site.family + " " + self.site.lang + ").")
        if "check_all_pages" in self.site.config and self.site.config["check_all_pages"]: #si fonction activée sur le wiki
            for page_name in self.site.all_pages(ns=0): #parcours de toutes les pages de l'espace principal
                page = self.site.page(page_name)
                pywikibot.output("Page : " + page_name)
                if not ("disable_vandalism" in self.site.config and self.site.config["disable_vandalism"]):
                    #détection vandalismes
                    self.check_vandalism(page)
                if "correct_redirects" in self.site.config and self.site.config["correct_redirects"] and page.isRedirectPage():
                    pywikibot.output("Correction de redirection sur la page " + str(page))
                    redirect = page.redirects() #Correction redirections
                edit_replace = page.edit_replace() #Recherches-remplacements
                pywikibot.output(str(edit_replace) + " recherche(s)-remplacement(s) sur la page " + str(page) + ".")
                if not ("disable_del_categories" in self.site.config and self.site.config["disable_del_categories"]) and page.page_ns != 2:
                    pywikibot.output("Suppression des catégories inexistantes sur la page " + str(page))
                    del_categories_no_exists = page.del_categories_no_exists() #Suppression 
                    if del_categories_no_exists != []:
                        pywikibot.output("Catégories retirées " + ", ".join(del_categories_no_exists))
                    else:
                        pywikibot.output("Aucune catégorie à retirer.")
                if self.site.family == "dicoado": #Dico des Ados
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
                                        try:
                                            bt = traceback.format_exc()
                                            pywikibot.error(bt)
                                        except UnicodeError:
                                            pass
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
                                        try:
                                            bt = traceback.format_exc()
                                            pywikibot.error(bt)
                                        except UnicodeError:
                                            pass
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
                                        try:
                                            bt = traceback.format_exc()
                                            pywikibot.error(bt)
                                        except UnicodeError:
                                            pass
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
                                        try:
                                            bt = traceback.format_exc()
                                            pywikibot.error(bt)
                                        except UnicodeError:
                                            pass
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
                                        try:
                                            bt = traceback.format_exc()
                                            pywikibot.error(bt)
                                        except UnicodeError:
                                            pass
                            if "|son=LL-Q150" in page.text:
                                page.text = page.text.replace("|son=LL-Q150", "|prononciation=LL-Q150")
                            if page.text != page_text_old:
                                page.save("maintenance")
                    except Exception as e:
                        try:
                            bt = traceback.format_exc()
                            pywikibot.error(bt)
                        except UnicodeError:
                            pass
        if "clear_talks" in self.site.config and self.site.config["clear_talks"]: #si fonction activée sur le wiki
            #Nettoyage des PDDs d'IPs (créer Modèle:Avertissement effacé)
            for page_name in self.site.all_pages(ns=3, start="1", end="A"):
                pywikibot.output("Page : " + page_name)
                if (page_name.count(".") == 3 or page_name.count(":") == 8):
                    user_talk = pywikibot.User(self.site.site, ":".join(page_name.split(":")[1:]))
                    if user_talk.isAnonymous():
                        page = self.site.page(page_name)
                        pywikibot.output("PDD d'IP")
                        if page.page_ns == 3 and (page.contributor_name != self.site.user_wiki or "<!-- level" in page.text) and abs((self.datetime_utcnow - page.latest_revision.timestamp).days) > self.site.days_clean_warnings:
                            pywikibot.output("Suppression des avertissements de la page " + page_name)
                            try:
                                if self.site.lang_bot == "fr":
                                    page.put("{{Avertissement effacé|{{subst:#time: j F Y}}}}", "Anciens messages effacés", minor=False, botflag=True)
                                else:
                                    page.put("{{Warning cleared|{{subst:#time: j F Y}}}}", "Old messages cleared", minor=False, botflag=True)
                            except Exception as e:
                                try:
                                    bt = traceback.format_exc()
                                    pywikibot.error(bt)
                                except UnicodeError:
                                    pass
                        else:
                            pywikibot.output("Pas d'avertissement à effacer")
                    else:
                        pywikibot.output("Pas une PDD d'IP")
                else:
                    pywikibot.output("Pas une PDD d'IP")

    def task_every_day(self):
        self.task_every_10minutes(True)

    def task_every_10minutes(self, task_day=False):
        detailed_diff_info = {}
        if task_day: #Une fois par jour, parcours de toutes les RC du jour
            pywikibot.output("Tâches réalisées tous les jours (" + self.site.family + " " + self.site.lang + ").")
            time1hour = self.datetime_utcnow - datetime.timedelta(hours = 24)
            pywikibot.output("Récupération des RC des 24 dernières heures sur " + self.site.family + " " + self.site.lang + "...")
            self.site.rc_pages(timestamp=time1hour.strftime("%Y%m%d%H%M%S"), rctoponly=False, show_trusted=True)
        else: #Sinon, parcours des RC des 10 dernières minutes
            pywikibot.output("Tâches réalisées une fois toutes les 10 minutes (" + self.site.family + " " + self.site.lang + ").")
            time1hour = self.datetime_utcnow - datetime.timedelta(minutes = 10)
            pywikibot.output("Récupération des RC des 10 dernières minutes sur " + self.site.family + " " + self.site.lang + "...")
            self.site.rc_pages(timestamp=time1hour.strftime("%Y%m%d%H%M%S"))
        pages_checked = [] #pages vérifiées (pour éviter de revérifier la page)
        for page_info in self.site.diffs_rc:
            #parcours des modifications récentes
            page_name = page_info["title"]
            page = self.site.page(page_name)
            if page.special or not page.exists(): #passage des pages spéciales ou inexistantes
                continue
            pywikibot.output("Page : " + page_name)
            if task_day: #Ajout de la modif dans les stats
                try:
                    vandalism_score = page.vandalism_score(page_info["revid"], page_info["old_revid"])
                    detailed_diff_info = self.site.add_detailed_diff_info(detailed_diff_info, page_info, page.text_page_oldid, page.text_page_oldid2, vandalism_score)
                except Exception as e:
                    try:
                        bt = traceback.format_exc()
                        pywikibot.error(bt)
                    except UnicodeError:
                        pass
            if page_name in pages_checked: #passage des pages déjà vérifiées
                continue
            if page.isRedirectPage():
                if "correct_redirects" in self.site.config and self.site.config["correct_redirects"]:
                    pywikibot.output("Correction de redirection sur la page " + str(page))
                    redirect = page.redirects() #Correction redirections
                else:
                    pywikibot.output("La page " + str(page) + " est une redirection.")
            else:
                if not ("disable_vandalism" in self.site.config and self.site.config["disable_vandalism"]):
                    #détection vandalismes
                    self.check_vandalism(page)
                if not ("disable_ai" in self.site.config and self.site.config["disable_ai"]):
                    #utilisation de l'IA pour détecter les vandalismes
                    self.check_vandalism_ai(page)
                if page.page_ns == 0:
                    #détection copies de Wikipédia
                    if "check_WP" in self.site.config and self.site.config["check_WP"] and len(page.text.strip()) > 0:
                        self.check_WP(page)
                    edit_replace = page.edit_replace() #Recherches-remplacements
                    pywikibot.output(str(edit_replace) + " recherche(s)-remplacement(s) sur la page " + str(page) + ".")
                if not ("disable_del_categories" in self.site.config and self.site.config["disable_del_categories"]) and task_day and page.page_ns != 2:
                    pywikibot.output("Suppression des catégories inexistantes sur la page " + str(page))
                    try:
                        del_categories_no_exists = page.del_categories_no_exists() #Suppression 
                        if del_categories_no_exists != []:
                            pywikibot.output("Catégories retirées " + ", ".join(del_categories_no_exists))
                        else:
                            pywikibot.output("Aucune catégorie à retirer.")
                    except Exception as e:
                        try:
                            bt = traceback.format_exc()
                            pywikibot.error(bt)
                        except UnicodeError:
                            pass
                pages_checked.append(page_name)
        if task_day: #Tâches journalières (après passage des RC)
            self.site.get_trusted() #récupération des utilisateurs ignorés par le bot
            #Statistiques journalières
            scores_n = {}
            scores_n_reverted = {}
            n_ip_contribs = 0
            n_users_contribs = 0
            n_ip_contribs_reverted = 0
            n_users_contribs_reverted = 0
            ip_list = []
            users_list = []
            ip_list_reverted = []
            users_list_reverted = []
            for diff in detailed_diff_info: #Calcul du nombre de modifs révoquées par score
                if "score" in detailed_diff_info[diff] and not detailed_diff_info[diff]["trusted"]:
                    if detailed_diff_info[diff]["score"] not in scores_n:
                        scores_n[detailed_diff_info[diff]["score"]] = 1
                        scores_n_reverted[detailed_diff_info[diff]["score"]] = 0
                    else:
                        scores_n[detailed_diff_info[diff]["score"]] += 1
                    if detailed_diff_info[diff]["anon"]:
                        n_ip_contribs += 1
                        if detailed_diff_info[diff]["user"] not in ip_list:
                            ip_list.append(detailed_diff_info[diff]["user"])
                    else:
                        n_users_contribs += 1
                        if detailed_diff_info[diff]["user"] not in users_list:
                            users_list.append(detailed_diff_info[diff]["user"])
                    if detailed_diff_info[diff]["reverted"]:
                        scores_n_reverted[detailed_diff_info[diff]["score"]] += 1
                        if detailed_diff_info[diff]["anon"]:
                            n_ip_contribs_reverted += 1
                            if detailed_diff_info[diff]["user"] not in ip_list_reverted:
                                ip_list_reverted.append(detailed_diff_info[diff]["user"])
                        else:
                            n_users_contribs_reverted += 1
                            if detailed_diff_info[diff]["user"] not in users_list_reverted:
                                users_list_reverted.append(detailed_diff_info[diff]["user"])
            pywikibot.output("Sauvegarde des modifications récentes du jour.")
            with open("rc_" + self.site.family + "_" + self.site.lang + "_" + time1hour.strftime("%Y%m%d") + ".json", "w") as file:
                file.write(json.dumps(detailed_diff_info))
            pywikibot.output("Calcul des statistiques (contributions).")
            n_contribs = n_users_contribs+n_ip_contribs
            n_contribs_reverted = n_users_contribs_reverted+n_ip_contribs_reverted
            if n_ip_contribs != 0:
                prop_ip_contribs = n_ip_contribs_reverted/n_ip_contribs
            else:
                prop_ip_contribs = 0
            if n_users_contribs != 0:
                prop_user_contribs = n_users_contribs_reverted/n_users_contribs
            else:
                prop_user_contribs = 0
            if n_contribs != 0:
                prop_contribs = n_contribs_reverted/n_contribs
            else:
                prop_contribs = 0
            pywikibot.output("Calcul des statistiques (utilisateurs).")
            n_users_reverted = len(users_list_reverted)
            n_ip_reverted = len(ip_list_reverted)
            n_users = len(users_list)
            n_ip = len(ip_list)
            n_users_ip = n_users+n_ip
            n_users_ip_reverted = n_users_reverted+n_ip_reverted
            if n_ip != 0:
                prop_ip = n_ip_reverted/n_ip
            else:
                prop_ip = 0
            if n_users != 0:
                prop_user = n_users_reverted/n_users
            else:
                prop_user = 0
            if n_users_ip != 0:
                prop_users_ip = n_users_ip_reverted/n_users_ip
            else:
                prop_users_ip = 0
            scores_x = []
            scores_y = []
            scores_n_reverted_2 = []
            scores_n_2 = []
            for score_n in scores_n:
                if score_n < 0:
                    scores_x.append(abs(score_n))
                    scores_y.append(scores_n_reverted[score_n]/scores_n[score_n])
                    scores_n_reverted_2.append(scores_n_reverted[score_n])
                    scores_n_2.append(scores_n[score_n])
            with open("vand_" + self.site.family + "_" + self.site.lang + "_" + time1hour.strftime("%Y%m%d") + ".txt", "w") as file:
                for i in range(len(scores_x)):
                    file.write(str(scores_x[i]) + ":" + str(scores_n_reverted_2[i]) + "/" + str(scores_n_2[i]) + "\r\n")
            if prop_users_ip > 0:
                if len(scores_x) >= 4 and len(scores_y) >= 4:
                    try:
                        coeffs_curve, _ = curve_fit(curve, scores_x, scores_y, maxfev=1000000)
                        no_coeffs = False
                    except Exception as e:
                        try:
                            bt = traceback.format_exc()
                            pywikibot.error(bt)
                        except UnicodeError:
                            pass
                        no_coeffs = True
                else:
                    pywikibot.output("Pas assez de scores pour générer la fonction.")
                    no_coeffs = True
                with open("vand_f_" + self.site.family + "_" + self.site.lang + "_" + time1hour.strftime("%Y%m%d") + ".txt", "w") as file:
                    if not no_coeffs:
                        file.write(str(coeffs_curve))
                    else:
                        file.write("erreur")
                if webhooks_url[self.site.family] != None:
                    if self.site.lang_bot == "fr":
                        fields = [
                                {
                                  "name": "IP et nouveaux révoqués/Nombre total d'IP et nouveaux (non-Autoconfirmed) actifs",
                                  "value": str(n_ip_reverted+n_users_reverted) + "/" + str(n_users_ip) + " (" + str(round(prop_users_ip*100, 2)) + " %)",
                                  "inline": False
                                },
                                {
                                  "name": "IP révoquées/Nombre total d'IPs",
                                  "value": str(n_ip_reverted) + "/" + str(n_ip) + " (" + str(round(prop_ip*100, 2)) + " %)",
                                  "inline": True
                                },
                                {
                                  "name": "Nouveaux inscrits révoqués/Nouveaux inscrits (non-Autoconfirmed) actifs",
                                  "value": str(n_users_reverted) + "/" + str(n_users) + " (" + str(round(prop_user*100, 2)) + " %)",
                                  "inline": True
                                },
                                {
                                  "name": "Modifications révoquées/Modifications totales des nouveaux (IP + utilisateurs non-Autoconfirmed)",
                                  "value": str(n_contribs_reverted) + "/" + str(n_contribs) + " (" + str(round(prop_contribs*100, 2)) + " %)",
                                  "inline": False
                                },
                                {
                                  "name": "Modifications révoquées/Modifications IP",
                                  "value": str(n_ip_contribs_reverted) + "/" + str(n_ip_contribs) + " (" + str(round(prop_ip_contribs*100, 2)) + " %)",
                                  "inline": True
                                },
                                {
                                  "name": "Modifications révoquées/Modifications nouveaux utilisateurs inscrits (non-Autoconfirmed)",
                                  "value": str(n_users_contribs_reverted) + "/" + str(n_users_contribs) + " (" + str(round(prop_user_contribs*100, 2)) + " %)",
                                  "inline": True
                                }
                            ]
                        discord_msg = {'embeds': [
                                    {
                                          'title': "Statistiques sur " + self.site.family + " " + self.site.lang + " (dernières 24 h)",
                                          'description': "Statistiques sur la patrouille (humains et bot):",
                                          'color': 65535,
                                          'fields': fields
                                    }
                                ]
                            }
                    else:
                        fields = [
                                {
                                  "name": "Reverted users/Total new users (no Autoconfirmed) and IP number",
                                  "value": str(n_ip_reverted+n_users_reverted) + "/" + str(n_users_ip) + " (" + str(round(prop_users_ip*100, 2)) + " %)",
                                  "inline": False
                                },
                                {
                                  "name": "Reverted IP/Total IP number",
                                  "value": str(n_ip_reverted) + "/" + str(n_ip) + " (" + str(round(prop_ip*100, 2)) + " %)",
                                  "inline": True
                                },
                                {
                                  "name": "Reverted users/Total users number",
                                  "value": str(n_users_reverted) + "/" + str(n_users) + " (" + str(round(prop_user*100, 2)) + " %)",
                                  "inline": True
                                },
                                {
                                  "name": "Reverted edits/Total new users (no Autoconfirmed) and IP edits",
                                  "value": str(n_contribs_reverted) + "/" + str(n_contribs) + " (" + str(round(prop_contribs*100, 2)) + " %)",
                                  "inline": False
                                },
                                {
                                  "name": "Reverted edits/IP edits",
                                  "value": str(n_ip_contribs_reverted) + "/" + str(n_ip_contribs) + " (" + str(round(prop_ip_contribs*100, 2)) + " %)",
                                  "inline": True
                                },
                                {
                                  "name": "Reverted edits/New users (no Autoconfirmed) edits",
                                  "value": str(n_users_contribs_reverted) + "/" + str(n_users_contribs) + " (" + str(round(prop_user_contribs*100, 2)) + " %)",
                                  "inline": True
                                }
                            ]
                        discord_msg = {'embeds': [
                                    {
                                          'title': "Statistics about " + self.site.family + " " + self.site.lang + " (last 24 h)",
                                          'description': "Statistics about patrolling (humans and bot):",
                                          'color': 65535,
                                          'fields': fields
                                    }
                                ]
                            }
                    request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
        if self.site.family == "dicoado":
            #spécifiques aux Dico des Ados
            #remise à 0 du BàS du Dico des Ados
            bas = self.site.page("Dico:Bac à sable")
            bas_zero = self.site.page("Dico:Bac à sable/Zéro")
            if abs((self.datetime_utcnow - bas.latest_revision.timestamp).seconds) > 3600 and bas.text != bas_zero.text:
                pywikibot.output("Remise à zéro du bac à sable")
                bas.put(bas_zero.text, "Remise à zéro du bac à sable")
            for page_name in self.site.all_pages(ns=4, apprefix="Bac à sable/Test/"):
                if page_name != "Dico:Bac à sable/Zéro":
                    bas_page = self.site.page(page_name)
                    if abs((self.datetime_utcnow - bas_page.latest_revision.timestamp).seconds) > 7200 and "{{SI" not in bas_page.text:
                        pywikibot.output("SI de " + page_name)
                        bas_page.text = "{{SI|Remise à zéro du bac à sable}}\n" + bas_page.text
                        bas_page.save("Remise à zéro du bac à sable")
##          if self.site.lang_bot == "fr":
##              cat_files_no_exists = self.site.category("Category:Pages avec des liens de fichiers brisés")
##              for page_cat in cat_files_no_exists.get_pages(ns=0):
##                  pywikibot.output("Suppression des fichiers inexistantes sur la page " + page_cat)
##                  page_cat_get = self.site.page(page_cat)
##                  del_files_no_exists = page_cat_get.del_files_no_exists()
##                  if del_files_no_exists != []:
##                      pywikibot.output("Fichiers retirés " + ", ".join(del_files_no_exists))
##                  else:
##                      pywikibot.output("Aucun fichier à retirer.")

    def check_vandalism(self, page):
        page_name = page.page_name
        vandalism_score = page.vandalism_get_score_current()
        if page.vand_to_revert: #Révocation si modification inférieure ou égale au score de révocation
            page.revert()
        if vandalism_score < 0: #Webhook d'avertissement
            if webhooks_url[self.site.family] != None:
                vand_prob = vand_f(abs(vandalism_score))
                if vand_prob > 100:
                    vand_prob = 100
                detected = ""
                for vandalism_score_detect in page.vandalism_score_detect:
                    if vandalism_score_detect[0] == "add_regex":
                        detected += str(vandalism_score_detect[1]) + " - + " + str(vandalism_score_detect[2].group()) + "\n"
                    elif vandalism_score_detect[0] == "size":
                        detected += str(vandalism_score_detect[1]) + " - size = " + str(page.size) + " < " + vandalism_score_detect[2] + "\n"
                    elif vandalism_score_detect[0] == "diff":
                        if int(vandalism_score_detect[2]) > 0:
                            detected += str(vandalism_score_detect[1]) + " - diff > " + vandalism_score_detect[2] + "\n"
                        else:
                            detected += str(vandalism_score_detect[1]) + " - diff < " + vandalism_score_detect[2] + "\n"
                    elif vandalism_score_detect[0] == "del_regex":
                        detected += str(vandalism_score_detect[1]) + " - - " + str(vandalism_score_detect[2].group()) + "\n"
                    else:
                        detected += str(vandalism_score_detect[1]) + " - + " + str(vandalism_score_detect[2].group()) + "\n"
                if vandalism_score <= page.limit:
                    if self.site.lang_bot == "fr":
                        title = "Modification non-constructive révoquée sur " + self.site.lang + ":" + page_name
                        description = "Cette modification a été détectée comme non-constructive"
                    else:
                        title = "Unconstructive edit reverted on " + self.site.lang + ":" + page_name
                        description = "This edit has been detected as unconstructive"
                    color = 13371938
                elif vandalism_score <= page.limit2:
                    if self.site.lang_bot == "fr":
                        title = "Modification suspecte sur " + self.site.lang + ":" + page_name
                        description = "Cette modification est probablement non-constructive"
                    else:
                        title = "Edit maybe unconstructive on " + self.site.lang + ":" + page_name
                        description = "This edit is probably unconstructive"
                    color = 12138760
                else:
                    if self.site.lang_bot == "fr":
                        title = "Modification à vérifier sur " + self.site.lang + ":" + page_name
                        description = "Cette modification est peut-être non-constructive"
                    else:
                        title = "Edit to verify on " + self.site.lang + ":" + page_name
                        description = "This edit is maybe unconstructive"
                    color = 12161032
                if self.site.lang_bot == "fr":
                    fields = [
                            {
                              "name": "Score",
                              "value": str(vandalism_score),
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
                              "value": str(vandalism_score),
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
                request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
                for i in range(len(detected)//4096+1):
                    discord_msg = {'embeds': [
                            {
                                  'title': title,
                                  'description': detected[4096*i:4096*(i+1)],
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': color
                            }
                        ]
                    }
                    request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
                if page.alert_request:
                    if self.site.lang_bot == "fr":
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
                    request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")

    def check_vandalism_ai(self, page):
        if not page.contributor_is_trusted():
            diff = page.get_diff()
            if self.site.lang_bot == "fr":
                prompt = f"""Est-ce du vandalisme (indiquer la probabilité que ce soit du vandalisme en % et analyser la modification) ?
Date : {page.latest_revision.timestamp}
Wiki : {page.url}
Page : {page.page_name}
Diff :
{diff}
"""
            else:
                prompt = f"""Is it vandalism (indicate the probability that it is vandalism in % and analyze the modification)?
Date : {page.latest_revision.timestamp}
Wiki: {page.url}
Page: {page.page_name}
Diff:
{diff}
    """
            try:
                chat_response = client.chat.complete(
                    model = model,
                    messages = [
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ]
                )
                success = True
            except Exception as e:
                try:
                    bt = traceback.format_exc()
                    pywikibot.error(bt)
                except UnicodeError:
                    pass
                success = False
            if success:
                result_ai = chat_response.choices[0].message.content
                if self.site.lang_bot == "fr":
                    title = "Analyse de l'IA (Mistral) sur " + self.site.lang + ":" + page.page_name
                else:
                    title = "AI analysis (Mistral) on " + self.site.lang + ":" + page.page_name
                color = 12161032
                for i in range(len(result_ai)//4096+1):
                    discord_msg = {'embeds': [
                            {
                                'title': title,
                                'description': result_ai[4096*i:4096*(i+1)],
                                'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                'author': {'name': page.contributor_name},
                                'color': color
                            }
                        ]
                    }
                    request_site(webhooks_url_ai[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
            else:
                if self.site.lang_bot == "fr":
                    title = "Analyse de l'IA (Mistral) échouée sur " + self.site.lang + ":" + page.page_name
                else:
                    title = "AI analysis (Mistral) failed on " + self.site.lang + ":" + page.page_name
                color = 13371938
                discord_msg = {'embeds': [
                        {
                            'title': title,
                            'description': '',
                            'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                            'author': {'name': page.contributor_name},
                            'color': color
                        }
                    ]
                }
                request_site(webhooks_url_ai[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")

    def check_WP(self, page):
        page_name = page.page_name
        score_check_WP = page.check_WP()
        prob_WP = score_check_WP/len(page.text.strip())*100
        template_WP = "User:" + page.user_wiki + "/CopyWP"
        pywikibot.output("Probabilité de copie de Wikipédia de la page " + str(page) + " : " + str(prob_WP) + " % (" + str(score_check_WP) + " octets en commun/" + str(len(page.text.strip())) + " octets))")
        if prob_WP >= 90:
            if self.site.lang_bot == "fr":
                if template_WP not in page.text:
                    page.text = "{{" + template_WP + "|" + page_name + "|" + str(round(prob_WP, 2)) + "}}\n" + page.text
                    page.save("copie de WP", botflag=False, minor=False)
                fields = [
                        {
                          "name": "Probabilité de copie",
                          "value": str(round(prob_WP, 2)) + " %",
                          "inline": True
                        }
                    ]
                discord_msg = {'embeds': [
                            {
                                  'title': "Très probable copie de Wikipédia sur " + self.site.lang + ":" + page_name,
                                  'description': "Cette page copie très probablement Wikipédia.",
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': 13371938,
                                  'fields': fields
                            }
                        ]
                    }
            else:
                if template_WP not in page.text:
                    page.text = "{{" + template_WP + "|" + page.page_name + "|" + str(round(prob_WP, 2)) + "}}\n" + page.text
                    page.save("copy of WP")
                fields = [
                        {
                          "name": "Probability of copy",
                          "value": str(round(prob_WP, 2)) + " %",
                          "inline": True
                        }
                    ]
                discord_msg = {'embeds': [
                            {
                                  'title': "Most likely copy from Wikipedia on " + self.site.lang + ":" + page_name,
                                  'description': "This page most likely copies Wikipedia.",
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': 13371938,
                                  'fields': fields
                            }
                        ]
                    }
            request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
        elif prob_WP >= 75:
            if self.site.lang_bot == "fr":
                fields = [
                        {
                          "name": "Probabilité de copie",
                          "value": str(round(prob_WP, 2)) + " %",
                          "inline": True
                        }
                    ]
                discord_msg = {'embeds': [
                            {
                                  'title': "Probable copie de Wikipédia sur " + self.site.lang + ":" + page_name,
                                  'description': "Cette page copie probablement Wikipédia.",
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': 12138760,
                                  'fields': fields
                            }
                        ]
                    }
            else:
                fields = [
                        {
                          "name": "Probability of copy",
                          "value": str(round(prob_WP, 2)) + " %",
                          "inline": True
                        }
                    ]
                discord_msg = {'embeds': [
                            {
                                  'title': "Likely copy from Wikipedia on " + self.site.lang + ":" + page_name,
                                  'description': "This page likely copies Wikipedia.",
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': 12138760,
                                  'fields': fields
                            }
                        ]
                    }
            request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")
        elif prob_WP >= 50:
            if self.site.lang_bot == "fr":
                fields = [
                        {
                          "name": "Probabilité de copie",
                          "value": str(round(prob_WP, 2)) + " %",
                          "inline": True
                        }
                    ]
                discord_msg = {'embeds': [
                            {
                                  'title': "Possible copie de Wikipédia sur " + self.site.lang + ":" + page_name,
                                  'description': "Cette page copie possiblement Wikipédia.",
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': 12161032,
                                  'fields': fields
                            }
                        ]
                    }
            else:
                fields = [
                        {
                          "name": "Probability of copy",
                          "value": str(round(prob_WP, 2)) + " %",
                          "inline": True
                        }
                    ]
                discord_msg = {'embeds': [
                            {
                                  'title': "Possible copy from Wikipedia on " + self.site.lang + ":" + page_name,
                                  'description': "This page likely copies Wikipedia.",
                                  'url': page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                                  'author': {'name': page.contributor_name},
                                  'color': 12161032,
                                  'fields': fields
                            }
                        ]
                    }
            request_site(webhooks_url[self.site.family], headers, json.dumps(discord_msg).encode("utf-8"), "POST")

    def execute(self):
        self.datetime_utcnow = datetime.datetime.utcnow()
        month = int(self.datetime_utcnow.strftime("%m"))
        day = int(self.datetime_utcnow.strftime("%d"))
        while True:
            self.datetime_utcnow = datetime.datetime.utcnow()
            try:
                if not self.ignore_task_month and (self.start_task_month or int(self.datetime_utcnow.strftime("%m")) != month): 
                    self.task_every_month()
                    self.start_task_month = False
                    month = int(self.datetime_utcnow.strftime("%m"))
                if self.start_task_day or int(self.datetime_utcnow.strftime("%d")) != day: 
                    self.task_every_day()
                    self.start_task_day = False
                    day = int(self.datetime_utcnow.strftime("%d"))
                self.task_every_10minutes()
            except Exception as e:
                try:
                    bt = traceback.format_exc()
                    pywikibot.error(bt)
                except UnicodeError:
                    pass
            time.sleep(600) #Pause de 10 minutes
