# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators, textlib
import base64, datetime, difflib, json, os, random, re, socket, time, urllib.request, urllib.error, urllib.parse, zlib
from config import *

class get_wiki:
    def __init__(self, family, lang, user_wiki):
        self.user_wiki = user_wiki
        self.family = family
        self.lang = lang
        self.config = {}
        config_filename = "config_" + family + "_" + lang + ".txt"
        open(config_filename, "a").close()
        with open(config_filename, "r") as config_wiki:
            config_file_content = config_wiki.read()
            if config_file_content != "":
                try:
                    self.config = json.loads(config_file_content.replace("\r", "").replace("\n", ""))
                except json.decoder.JSONDecodeError:
                    pywikibot.error("Erreur de configuration sur " + lang + "." + family)
        if "lang_bot" in self.config:
            self.lang_bot = self.config["lang_bot"]
        else:
            self.lang_bot = "en"
        if "days_clean_warnings" in self.config:
            self.days_clean_warnings = self.config["days_clean_warnings"]
        else:
            self.days_clean_warnings = 365
        self.site = pywikibot.Site(lang, family, self.user_wiki)
        self.fullurl = self.site.siteinfo["general"]["server"]
        self.protocol = self.fullurl.split("/")[0]
        if self.protocol == "":
            self.protocol = "https:"
        self.url = self.fullurl.split("/")[2]
        self.articlepath = self.site.siteinfo["general"]["articlepath"].replace("$1", "")
        self.scriptpath = self.site.siteinfo["general"]["scriptpath"]
        self.trusted = []

    def get_trusted(self):
        if "trusted_groups" in self.config:
            trusted_groups = self.config["trusted_groups"]
        else:
            trusted_groups = "sysop"
        url = "%s//%s%s/api.php?action=query&list=allusers&augroup=%s&aulimit=500&format=json" % (self.protocol, self.url, self.scriptpath, trusted_groups)
        aufrom = ""
        while aufrom != None:
            if aufrom != "":
                j = json.loads(request_site(url + "&aufrom=" + urllib.parse.quote(aufrom)))
            else:
                j = json.loads(request_site(url))
            try:
                trusted_query = j["query"]["allusers"]
            except KeyError:
                trusted_query = []
            try:
                aufrom = j["continue"]["aufrom"]
            except KeyError:
                aufrom = None
            for user_trusted in trusted_query:
                self.trusted.append(user_trusted["name"])

    def all_pages(self, n_pages=5000, ns=0, start=None, end=None, apfilterredir=None, apprefix=None, urladd=None):
        pages = []
        url = "%s//%s%s/api.php?action=query&list=allpages&aplimit=%s&apnamespace=%s&format=json" % (self.protocol, self.url, self.scriptpath, str(n_pages), str(ns))
        if start is not None:
            url += "&apfrom=" + start
        if end is not None:
            url += "&apto=" + end
        if apfilterredir is not None:
            url += "&apfilterredir=" + apfilterredir
        if apprefix is not None:
            url += "&apprefix=" + urllib.parse.quote(apprefix)
        if urladd is not None:
            url += urllib.parse.quote(urladd)
        apcontinue = ""
        while apcontinue != None:
            if apcontinue != "":
                j = json.loads(request_site(url + "&apcontinue=" + urllib.parse.quote(apcontinue)))
            else:
                j = json.loads(request_site(url))
            try:
                contribs = j["query"]["allpages"]
            except KeyError:
                return []
            try:
                apcontinue = j["continue"]["apcontinue"]
            except KeyError:
                apcontinue = None
            for contrib in contribs:
                pages.append(contrib["title"])
        return pages

    def problematic_redirects(self, type_redirects):
        pages = []
        url = "%s//%s%s/api.php?action=query&list=querypage&qppage=%s&qplimit=max&format=json" % (self.protocol, self.url, self.scriptpath, type_redirects)
        apcontinue = ""
        while apcontinue != None:
            if apcontinue != "":
                j = json.loads(request_site(url + "&apcontinue=" + urllib.parse.quote(apcontinue)))
            else:
                j = json.loads(request_site(url))
            try:
                results = j["query"]["querypage"]["results"]
            except KeyError:
                return []
            try:
                apcontinue = j["continue"]["apcontinue"]
            except KeyError:
                apcontinue = None
            for result in results:
                pages.append(result["title"])
        return pages

    def rc_pages(self, n_edits=5000, timestamp=None, rctoponly=True, show_trusted=False, namespace=None, timestamp_start=None):
        self.diffs_rc = []
        page_names = []
        url = "%s//%s%s/api.php?action=query&list=recentchanges&rclimit=%s&rcend=%s&rcprop=timestamp|title|user|ids|comment|tags&rctype=edit|new|categorize&rcshow=!bot&format=json" % (self.protocol, self.url, self.scriptpath, str(n_edits), str(timestamp))
        if timestamp_start:
            url += "&rcstart=" + str(timestamp_start)
        if rctoponly:
            url += "&rctoponly"
        if namespace != None:
            url += "&rcnamespace=" + namespace
        rccontinue = ""
        while rccontinue != None:
            if rccontinue != "":
                j = json.loads(request_site(url + "&rccontinue=" + rccontinue))
            else:
                j = json.loads(request_site(url))
            contribs = j["query"]["recentchanges"]
            try:
                rccontinue = j["continue"]["rccontinue"]
            except KeyError:
                rccontinue = None
            for contrib in contribs:
                if show_trusted or ("user" in contrib and contrib["user"] not in self.trusted):
                    self.diffs_rc.append(contrib)

    def page(self, page_wiki):
        return get_page(self, page_wiki)

    def category(self, page_wiki):
        return get_category(self, page_wiki)

    def add_detailed_diff_info(self, diff_info, page_info, old, new, vandalism_score):
        if page_info["revid"] not in diff_info:
            diff_info[page_info["revid"]] = {"reverted": False, "next_revid": -1}
        diff_info[page_info["revid"]]["score"] = vandalism_score
        diff_info[page_info["revid"]]["anon"] = "anon" in page_info
        diff_info[page_info["revid"]]["trusted"] = "user" in page_info and page_info["user"] in self.trusted
        if "user" in page_info:
            diff_info[page_info["revid"]]["user"] = page_info["user"]
        else:
            diff_info[page_info["revid"]]["user"] = ""
        diff_info[page_info["revid"]]["page"] = page_info["title"]
        diff_info[page_info["revid"]]["old"] = old
        diff_info[page_info["revid"]]["new"] = new
        if not diff_info[page_info["revid"]]["reverted"]:
            diff_info[page_info["revid"]]["reverted"] = diff_info[page_info["revid"]]["next_revid"] > 0 and not diff_info[page_info["revid"]]["trusted"] and diff_info[diff_info[page_info["revid"]]["next_revid"]]["reverted"] and "user" in page_info and diff_info[diff_info[page_info["revid"]]["next_revid"]]["user"] == page_info["user"]
        if page_info["old_revid"] != 0 and page_info["old_revid"] != -1:
            diff_info[page_info["old_revid"]] = {"reverted": False, "next_revid": page_info["revid"]}
            if "comment" in page_info:
                diff_info[page_info["old_revid"]]["reverted"] = "revert" in page_info["comment"].lower() or "révoc" in page_info["comment"].lower() or "cancel" in page_info["comment"].lower() or "annul" in page_info["comment"].lower()
        return diff_info


class get_page(pywikibot.Page):
    def __init__(self, source, title):
        self.source = source
        self.user_wiki = source.user_wiki
        self.lang = source.lang
        self.lang_bot = source.lang_bot
        self.page_name = title
        if self.page_name.split(":")[0].lower() == "special" or self.page_name.split(":")[0].lower() == "spécial":
            self.special = True
        else:
            self.special = False
            pywikibot.Page.__init__(self, self.source.site, self.page_name)
        self.new_page = None
        self.text_page_oldid = None
        self.text_page_oldid2 = None
        self.vand_to_revert = False
        self.reverted = False
        self.fullurl = self.source.site.siteinfo["general"]["server"] + self.source.site.siteinfo["general"]["articlepath"].replace("$1", self.page_name)
        self.protocol = self.fullurl.split("/")[0]
        if self.protocol == "":
            self.protocol = "https:"
        self.url = self.fullurl.split("/")[2]
        self.articlepath = self.source.site.siteinfo["general"]["articlepath"].replace("$1", "")
        self.scriptpath = self.source.site.siteinfo["general"]["scriptpath"]
        if not self.special:
            try:
                self.contributor_name = self.latest_revision.user
                self.page_ns = self.namespace()
                self.oldid = self.latest_revision_id
                self.size = len(self.text)
            except:
                self.contributor_name = ""
                self.page_ns = -1
                self.oldid = None
                self.size = None

        self.limit = -50
        self.limit2 = -30
        self.limit_ai = 98
        self.limit_ai2 = 90
        self.limit_ai3 = 50
        #Page d'alerte
        if "alert_page" in self.source.config:
            self.alert_page = datetime.datetime.now().strftime(self.source.config["alert_page"].replace("\r", "").replace("\n", ""))
        else:
            if self.lang_bot == "fr":
                self.alert_page = "Project:Alerte"
            else:
                self.alert_page = "Project:Alert"
        self.alert_request = False
        self.warn_level = -1

    def revert(self, summary=""):
        self.only_revert(summary)
        self.warn_revert(summary)

    def only_revert(self, summary=""):
        if self.text_page_oldid == None or self.text_page_oldid2 == None:
            self.get_text_page_old()
        if self.new_page:
            self.text = "{{subst:User:%s/VandalismDelete}}" % self.user_wiki
        else:
            self.text = self.text_page_oldid2
        if self.lang_bot == "fr":
            if summary != "":
                self.save("Annulation : " + summary, bot=False, minor=False)
            else:
                self.save("Annulation modification non-constructive", bot=False, minor=False)
        else:
            if summary != "":
                self.save("Revert : " + summary, bot=False, minor=False)
            else:
                self.save("Revert", bot=False, minor=False)
        self.reverted = True

    def get_warnings_user(self):
        self.talk = pywikibot.Page(self.source.site, "User Talk:%s" % self.contributor_name)
        if ("averto-1" in self.talk.text.lower() or "niveau=1" in self.talk.text.lower() or "level=1" in self.talk.text.lower()) and "averto-2" not in self.talk.text.lower() and "niveau=2" not in self.talk.text.lower() and "level=2" not in self.talk.text.lower(): #averti 2 fois
            self.warn_level = 2
        elif ("averto-0" in self.talk.text.lower() or "niveau=0" in self.talk.text.lower() or "level=0" in self.talk.text.lower()) and "averto-1" not in self.talk.text.lower() and "niveau=1" not in self.talk.text.lower() and "level=1" not in self.talk.text.lower(): #averti une fois
            self.warn_level = 1
        elif "averto-0" not in self.talk.text.lower() and "niveau=0" not in self.talk.text.lower() and "level=0" not in self.talk.text.lower(): #pas averti
            self.warn_level = 0

    def warn_revert(self, summary=""):
        if self.warn_level < 0:
            self.get_warnings_user()
        if self.warn_level >= 2: #averti 2 fois
            alert = pywikibot.Page(self.source.site, self.alert_page)
            alert.text = alert.text + "\n{{subst:User:%s/Alert|%s}}" % (self.user_wiki, self.contributor_name)
            if self.lang_bot == "fr":
                alert.save("Alerte vandalisme", bot=False, minor=False)
            else:
                alert.save("Vandalism alert", bot=False, minor=False)
            self.talk.text = self.talk.text + "\n{{subst:User:%s/Vandalism2|%s|%s}} <!-- level=2 -->" % (self.user_wiki, self.page_name, summary)
            if self.lang_bot == "fr":
                self.talk.save("Avertissement 2", bot=False, minor=False)
            else:
                self.talk.save("Warning 2", bot=False, minor=False)
            self.alert_request = True
        elif self.warn_level == 1: #averti une fois
            self.talk.text = self.talk.text + "\n{{subst:User:%s/Vandalism1|%s|%s}} <!-- level=1 -->" % (self.user_wiki, self.page_name, summary)
            if self.lang_bot == "fr":
                self.talk.save("Avertissement 1", bot=False, minor=False)
            else:
                self.talk.save("Warning 1", bot=False, minor=False)
        else: #pas averti
            self.talk.text = self.talk.text + "\n{{subst:User:%s/Vandalism0|%s|%s}} <!-- level=0 -->" % (self.user_wiki, self.page_name, summary)
            if self.lang_bot == "fr":
                self.talk.save("Avertissement 0", bot=False, minor=False)
            else:
                self.talk.save("Warning 0", bot=False, minor=False)

    def vandalism_get_score_current(self): #Score sur la version actuelle en ignorant les contributeurs expérimentés
        if self.contributor_is_trusted():
            return 0
        vand = self.vandalism_score()
        if vand <= self.limit:
            self.vand_to_revert = True
        elif vand <= self.limit2:
            self.get_warnings_user()
            if self.warn_level > 0:
                self.vand_to_revert = True
            else:
                self.vand_to_revert = False
        else:
            self.vand_to_revert = False
        return vand

    def contributor_is_trusted(self):
        return self.contributor_name == self.user_wiki or self.contributor_name in self.source.trusted or (self.page_ns == 2 and self.contributor_name in self.page_name)

    def get_text_page_old(self, revision_oldid=None, revision_oldid2=None): #revision_oldid : nouvelle version/version à vérifier, revision_oldid2 : ancienne version/version à comparer
        oldid = -1
        if revision_oldid is not None:
            text_page_oldid = self.getOldVersion(oldid = revision_oldid)
        else:
            text_page_oldid = self.text
        if revision_oldid2 is not None:
            oldid = revision_oldid2
        else:
            try:
                revisions_list = list(self.revisions())
            except:
                revisions_list = []
            for revision in revisions_list:
                if revision.user != self.contributor_name and (revision_oldid is None or revision.revid <= revision_oldid):
                    oldid = revision.revid
                    break
        if oldid != -1 and oldid != 0:
            self.new_page = False
            text_page_oldid2 = self.getOldVersion(oldid = oldid)
        else:
            self.new_page = True
            text_page_oldid2 = ""
        if text_page_oldid is None:
            text_page_oldid = ""
        if text_page_oldid2 is None:
            text_page_oldid2 = ""
        self.text_page_oldid = text_page_oldid
        self.text_page_oldid2 = text_page_oldid2

    def get_diff(self):
        differ = difflib.Differ()
        diff = list(differ.compare(self.text_page_oldid2.splitlines(), self.text_page_oldid.splitlines()))
        diff_text = '\n'.join(diff)
        return diff_text

    def vandalism_score(self, revision_oldid=None, revision_oldid2=None): #Score sur le diff en paramètres en incluant les utilisateurs expérimentés
        self.vandalism_score_detect = []
        self.get_text_page_old(revision_oldid, revision_oldid2)
        regex_vandalisms_0_filename = "regex_vandalisms_0.txt"
        regex_vandalisms_0_local_filename = "regex_vandalisms_0_" + self.source.family + "_" + self.lang + ".txt"
        size_vandalisms_0_filename = "size_vandalisms_0.txt"
        diff_vandalisms_0_filename = "diff_vandalisms_0.txt"
        regex_vandalisms_del_0_filename = "regex_vandalisms_del_0.txt"
        regex_vandalisms_del_0_local_filename = "regex_vandalisms_del_0_" + self.source.family + "_" + self.lang + ".txt"
        open(regex_vandalisms_0_filename, "a").close()
        open(regex_vandalisms_0_local_filename, "a").close()
        open(size_vandalisms_0_filename, "a").close()
        open(diff_vandalisms_0_filename, "a").close()
        open(regex_vandalisms_del_0_filename, "a").close()
        open(regex_vandalisms_del_0_local_filename, "a").close()
        vand = 0
        if self.page_ns == 0:
            with open(regex_vandalisms_0_filename, "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    regex = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    regex_detect = regex_vandalism(regex, self.text_page_oldid, self.text_page_oldid2)
                    if regex_detect:
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["add_regex", score, regex_detect])
                        vand += score
            with open(regex_vandalisms_0_local_filename, "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    regex = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    regex_detect = regex_vandalism(regex, self.text_page_oldid, self.text_page_oldid2)
                    if regex_detect:
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["add_regex", score, regex_detect])
                        vand += score
            with open(size_vandalisms_0_filename, "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    size = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    if len(self.text_page_oldid) < int(size):
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["size", score, size])
                        vand += score
            with open(diff_vandalisms_0_filename, "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    diff = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    if (int(diff) < 0 and len(self.text_page_oldid) - len(self.text_page_oldid2) <= int(diff)) or (int(diff) >= 0 and len(self.text_page_oldid) - len(self.text_page_oldid2) >= int(diff)):
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["diff", score, diff])
                        vand += score
            with open(regex_vandalisms_del_0_filename, "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    regex = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    regex_detect = regex_vandalism(regex, self.text_page_oldid2, self.text_page_oldid)
                    if regex_detect:
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["del_regex", score, regex_detect])
                        vand += score
            with open(regex_vandalisms_del_0_local_filename, "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    regex = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    regex_detect = regex_vandalism(regex, self.text_page_oldid2, self.text_page_oldid)
                    if regex_detect:
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["del_regex", score, regex_detect])
                        vand += score
        return vand

    def check_WP(self, page_name_WP=None, diff=None, lang=None):
        if page_name_WP == None:
            page_name_WP = self.page_name
        if diff == None:
            text_to_check = self.text.strip()
        else:
            text_to_check = self.getOldVersion(oldid = diff)
        if lang is None:
            lang = self.lang_bot
        url = "%s//%s%s/api.php?action=query&prop=revisions&rvprop=content&rvslots=*&titles=%s&formatversion=2&format=json" % ("https:", lang + ".wikipedia.org", "/w", urllib.parse.quote(page_name_WP))
        j = json.loads(request_site(url))
        if "missing" in j["query"]["pages"][0]:
            return 0
        page_text_WP = j["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
        score = 0
        matcher = difflib.SequenceMatcher(a=text_to_check, b=page_text_WP)
        for match in matcher.get_matching_blocks():
            score += match.size
        if score < 10 and lang == "en":
            return self.check_WP(page_name_WP, diff, "simple")
        else:
            return score

    def edit_replace(self):
        file1 = "replace1_" + self.source.family + "_" + self.lang + ".txt"
        file2 = "replace2_" + self.source.family + "_" + self.lang + ".txt"
        open(file1, "a").close()
        open(file2, "a").close()
        text_page = self.text
        n = 0
        with open(file1, "r") as replace1_file:
            with open(file2, "r") as replace2_file:
                replace1_lines, replace2_lines = replace1_file.readlines(), replace2_file.readlines()
                for replace1 in replace1_lines:
                    replace2 = replace2_lines[n]
                    pywikibot.output("Remplacement du regex %s par %s..." % (replace1, replace2))
                    self.text = re.sub(replace1, replace2, text_page)
                    if self.text != text_page:
                        n += 1
                        text_page = self.text
                        pywikibot.output("Le regex %s a été trouvé et va être remplacé par %s." % (replace1, replace2))
        if n > 0:
            if self.lang_bot == "fr":
                self.save(str(n) + " recherches-remplacements")
            else:
                self.save(str(n) + " find-replaces")
            pywikibot.output(str(n) + " recherches-remplacements effectuées (" + str(self) + ")")
        else:
            pywikibot.output("Rien à remplacer.")
        return n

    def redirects(self):
        type_redirect = None
        try:
            page_redirect = self.getRedirectTarget()
            if not page_redirect.exists():
                type_redirect = "broken"
                if self.lang_bot == "fr":
                    self.put("{{User:%s/RedirectDelete}}" % self.user_wiki, "Demande suppression redirection cassée")
                else:
                    self.put("{{User:%s/RedirectDelete}}" % self.user_wiki, "Delete broken redirect")
                pywikibot.output("Redirecton cassée demandée à la suppression.")
            elif page_redirect.isRedirectPage():
                type_redirect = "double"
                if self.lang_bot == "fr":
                    self.put("#REDIRECT[[%s]]" % page_redirect.getRedirectTarget().title(), "Correction redirection")
                else:
                    self.put("#REDIRECT[[%s]]" % page_redirect.getRedirectTarget().title(), "Correct redirect")
                pywikibot.output("Double redirection corrigée.")
            else:
                type_redirect = "correct"
                pywikibot.output("Redirection correcte.")
        except pywikibot.exceptions.CircularRedirectError:
            type_redirect = "circular"
            if self.lang_bot == "fr":
                self.put("{{User:%s/RedirectDelete|circular=True}}" % self.user_wiki, "Demande suppression redirection en boucle")
            else:
                self.put("{{User:%s/RedirectDelete|circular=True}}" % self.user_wiki, "Delete circular redirect")
            pywikibot.output("Redirecton en boucle demandée à la suppression.")
        return type_redirect

    def category_page(self, category_name):
        for category in self.categories():
            if category.title() == category_name:
                return True
        return False

    def del_categories_no_exists(self):
        categories_list = []
        for category in self.categories():
            if not category.exists():
                self.text = re.sub(r"(?i)\[\[" + re.escape(category.title()) + r"(\|.*)?\]\]", "", self.text, flags=re.IGNORECASE)
                categories_list.append(category.title())
        if categories_list != []:
            if self.lang_bot == "fr":
                self.save("Suppression des catégories inexistantes")
            else:
                self.save("Deleting non-existent categories")
        return categories_list

    def del_files_no_exists(self):
        files_list = []
        for file_page in self.imagelinks():
            if not file_page.exists():
                self.text = re.sub(r"\[\[(?i)" + re.escape(file_page.title()) + r"(\|.*)?\]\]", "", self.text, flags=re.IGNORECASE)
                files_list.append(file_page.title())
        if files_list != []:
            self.save("Suppression des fichiers inexistantes")
        return files_list

class get_category(get_page, pywikibot.Category):
    def __init__(self, source, title):
        pywikibot.Category.__init__(self, source.site, title)
        get_page.__init__(self)

    def cat_pages(self):
        gen = pagegenerators.CategorizedPageGenerator(self)
        i = 0
        for page in gen:
            i += 1
        return i

    def get_pages(self, ns=None):
        gen = pagegenerators.CategorizedPageGenerator(self)
        pages = []
        for page in gen:
            if page.namespace() == ns or ns is None:
                pages.append(page.title())
        return pages

def request_site(url, headers=headers, data=None, method="GET"):
    site = urllib.request.Request(url, headers=headers, data=data, method=method)
    page = urllib.request.urlopen(site)
    return page.read().decode("utf-8")

def regex_vandalism(regex, text_page1, text_page2, ignorecase=True):
    if ignorecase:
        re1 = re.search(regex, text_page1, re.IGNORECASE)
        re2 = re.search(regex, text_page2, re.IGNORECASE)
    else:
        re1 = re.search(regex, text_page1)
        re2 = re.search(regex, text_page2)
    if re1 and not re2:
        return re1
    else:
        return None
