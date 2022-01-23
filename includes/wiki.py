# -*- coding: utf-8 -*-

import pywikibot
from pywikibot import pagegenerators, textlib
import base64, datetime, json, os, random, re, socket, time, urllib.request, urllib.error, urllib.parse, zlib
from config import *

class get_wiki:
    def __init__(self, family, lang, user_wiki):
        self.user_wiki = user_wiki
        self.family = family
        self.lang = lang
        self.config = {}
        open("config_" + family + "_" + lang + ".txt", "a").close()
        with open("config_" + family + "_" + lang + ".txt", "r") as config_wiki:
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
        if "trusted_groups" in self.config:
            self.trusted_groups = self.config["trusted_groups"]
        else:
            self.trusted_groups = "sysop|bureaucrat"
        self.site = pywikibot.Site(lang, family, self.user_wiki)
        self.fullurl = self.site.siteinfo["general"]["server"]
        self.protocol = self.fullurl.split("/")[0]
        if self.protocol == "":
            self.protocol = "https:"
        self.url = self.fullurl.split("/")[2]
        self.articlepath = self.site.siteinfo["general"]["articlepath"].replace("$1", "")
        self.scriptpath = self.site.siteinfo["general"]["scriptpath"]
        url = "%s//%s%s/api.php?action=query&list=allusers&augroup=%s&aulimit=500&format=json" % (self.protocol, self.url, self.scriptpath, self.trusted_groups)
        self.trusted = []
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

    def site_info(self, prop, info):
        return self.site.siteinfo["general"][prop][info]

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

    def rc_pages(self, n_edits=5000, timestamp=None, rctoponly=True, show_trusted=False, return_type="title"):
        self.diffs_rc = []
        page_names = []
        url = "%s//%s%s/api.php?action=query&list=recentchanges&rclimit=%s&rcend=%s&rcprop=timestamp|title|user|ids|comment&rctype=edit|new|categorize&rcshow=!bot&format=json" % (self.protocol, self.url, self.scriptpath, str(n_edits), str(timestamp))
        if rctoponly:
            url += "&rctoponly"
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
                if show_trusted or contrib["user"] not in self.trusted:
                    self.diffs_rc.append(contrib)
                    if return_type and contrib[return_type] not in page_names:
                        page_names.append(contrib[return_type])
        return page_names

    def page(self, page_wiki):
        return get_page(self, page_wiki)

    def category(self, page_wiki):
        return get_category(self, page_wiki)

    def get_scores(self, hours=24):
        scores = {}
        time1hour = datetime.datetime.utcnow() - datetime.timedelta(hours=hours)
        self.rc_pages(timestamp=time1hour.strftime("%Y%m%d%H%M%S"), rctoponly=False)
        for page_info in self.diffs_rc:
            page = self.page(page_info["title"])
            try:
                vandalism_score = page.vandalism_score(page_info["revid"], page_info["old_revid"])
                if page_info["revid"] not in scores:
                    scores[page_info["revid"]] = {"reverted": False}
                scores[page_info["revid"]]["score"] = vandalism_score
                scores[page_info["revid"]]["anon"] = "anon" in page_info
                scores[page_info["revid"]]["user"] = page_info["user"]
                scores[page_info["revid"]]["page"] = page_info["title"]
                if page_info["old_revid"] != 0 and page_info["old_revid"] != -1:
                    scores[page_info["old_revid"]] = {"reverted": False}
                    if "comment" in page_info:
                        scores[page_info["old_revid"]]["reverted"] = "revert" in page_info["comment"].lower() or "révoc" in page_info["comment"].lower() or "cancel" in page_info["comment"].lower() or "annul" in page_info["comment"].lower()
                pywikibot.output(scores[page_info["revid"]])
            except Exception as e:
                pywikibot.error(e)
        return scores


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
        self.text_page_oldid = None
        self.text_page_oldid2 = None
        self.init_page()

    def init_page(self):
        self.fullurl = self.source.site.siteinfo["general"]["server"] + self.source.site.siteinfo["general"]["articlepath"].replace("$1", self.page_name)
        self.protocol = self.fullurl.split("/")[0]
        if self.protocol == "":
            self.protocol = "https:"
        self.url = self.fullurl.split("/")[2]
        self.articlepath = self.source.site.siteinfo["general"]["articlepath"].replace("$1", "")
        self.scriptpath = self.source.site.siteinfo["general"]["scriptpath"]
        if not self.special:
            try:
                self.contributor_name = self.userName()
                self.page_ns = self.namespace()
                self.oldid = self.latest_revision_id
            except:
                self.contributor_name = ""
                self.page_ns = -1
                self.oldid = None

        self.limit = -50
        self.limit2 = -30
        #Page d'alerte
        if "alert_page" in self.source.config:
            self.alert_page = datetime.datetime.now().strftime(self.source.config["alert_page"].replace("\r", "").replace("\n", ""))
        else:
            if self.lang_bot == "fr":
                self.alert_page = "Project:Alerte"
            else:
                self.alert_page = "Project:Alert"
        self.alert_request = False

    def revert(self):
        if self.text_page_oldid == None or self.text_page_oldid2 == None:
            self.get_text_page_old()
        self.text = self.text_page_oldid2
        if self.lang_bot == "fr":
            self.save("Annulation modification non-constructive", botflag=False, minor=False)
        else:
            self.save("Revert", botflag=False, minor=False)
        talk = pywikibot.Page(self.source.site, "User Talk:%s" % self.contributor_name)
        if ("averto-1" in talk.text.lower() or "niveau=1" in talk.text.lower() or "level=1" in talk.text.lower()) and "averto-2" not in talk.text.lower() and "niveau=2" not in talk.text.lower() and "level=2" not in talk.text.lower(): #averti 2 fois
            alert = pywikibot.Page(self.source.site, self.alert_page)
            alert.text = alert.text + "\n{{subst:User:%s/Alert|%s}}" % (self.user_wiki, self.contributor_name)
            if self.lang_bot == "fr":
                alert.save("Alerte vandalisme", botflag=False, minor=False)
            else:
                alert.save("Vandalism alert", botflag=False, minor=False)
            talk.text = talk.text + "\n{{subst:User:%s/Vandalism2|%s}} <!-- level=2 -->" % (self.user_wiki, self.page_name)
            if self.lang_bot == "fr":
                talk.save("Avertissement 2", botflag=False, minor=False)
            else:
                talk.save("Warning 2", botflag=False, minor=False)
            self.alert_request = True
        elif ("averto-0" in talk.text.lower() or "niveau=0" in talk.text.lower() or "level=0" in talk.text.lower()) and "averto-1" not in talk.text.lower() and "niveau=1" not in talk.text.lower() and "level=1" not in talk.text.lower(): #averti une fois
            talk.text = talk.text + "\n{{subst:User:%s/Vandalism1|%s}} <!-- level=1 -->" % (self.user_wiki, self.page_name)
            if self.lang_bot == "fr":
                talk.save("Avertissement 1", botflag=False, minor=False)
            else:
                talk.save("Warning 1", botflag=False, minor=False)
        elif "averto-0" not in talk.text.lower() and "niveau=0" not in talk.text.lower() and "level=0" not in talk.text.lower(): #pas averti
            talk.text = talk.text + "\n{{subst:User:%s/Vandalism0|%s}} <!-- level=0 -->" % (self.user_wiki, self.page_name)
            if self.lang_bot == "fr":
                talk.save("Avertissement 0", botflag=False, minor=False)
            else:
                talk.save("Warning 0", botflag=False, minor=False)

    def vandalism_revert(self):
        if self.contributor_name == self.user_wiki:
            return 0
        vand = self.vandalism_score()
        revert = vand <= self.limit
        if vand < 0:
            if self.contributor_name in self.source.trusted:
                return 0
        if self.page_ns == 2:
            if self.contributor_name in self.page_name:
                return 0
        if vand <= self.limit:
            pywikibot.output("Modification non-constructive détectée (%s)." % str(vand))
        elif vand <= self.limit2:
            pywikibot.output("Modification suspecte détectée (%s)." % str(vand))
        elif vand < 0:
            pywikibot.output("Modification à vérifier détectée (%s)." % str(vand))
        else:
            pywikibot.output("Pas de modification suspecte détectée (%s)." % str(vand))
        if revert:
            self.revert()
        return vand

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
            text_page_oldid2 = self.getOldVersion(oldid = oldid)
        else:
            text_page_oldid2 = "{{subst:User:%s/VandalismDelete}}" % self.user_wiki
        if text_page_oldid is None:
            text_page_oldid = ""
        if text_page_oldid2 is None:
            text_page_oldid2 = ""
        self.text_page_oldid = text_page_oldid
        self.text_page_oldid2 = text_page_oldid2

    def vandalism_score(self, revision_oldid=None, revision_oldid2=None):
        self.vandalism_score_detect = []
        self.get_text_page_old(revision_oldid, revision_oldid2)
        open("regex_vandalisms_0.txt", "a").close()
        open("size_vandalisms_0.txt", "a").close()
        open("diff_vandalisms_0.txt", "a").close()
        open("regex_vandalisms_del_0.txt", "a").close()
        vand = 0
        if self.page_ns == 0:
            with open("regex_vandalisms_0.txt", "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    regex = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    regex_detect = regex_vandalism(regex, self.text_page_oldid, self.text_page_oldid2)
                    if regex_detect:
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["add_regex", score, regex_detect])
                        vand += score
            with open("size_vandalisms_0.txt", "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    size = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    if len(self.text_page_oldid) < int(size):
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["size", score, size])
                        vand += score
            with open("diff_vandalisms_0.txt", "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    diff = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    if (int(diff) < 0 and len(self.text_page_oldid) - len(self.text_page_oldid2) <= int(diff)) or (int(diff) >= 0 and len(self.text_page_oldid) - len(self.text_page_oldid2) >= int(diff)):
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["diff", score, diff])
                        vand += score
            with open("regex_vandalisms_del_0.txt", "r") as regex_vandalisms_file:
                for regex_vandalisms in regex_vandalisms_file.readlines():
                    regex = regex_vandalisms[0:len(regex_vandalisms)-len(regex_vandalisms.split(":")[-1])-1]
                    regex_detect = regex_vandalism(regex, self.text_page_oldid2, self.text_page_oldid)
                    if regex_detect:
                        score = int(regex_vandalisms.split(":")[-1])
                        self.vandalism_score_detect.append(["del_regex", score, regex_detect])
                        vand += score

        return vand

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
        except pywikibot.exceptions.CircularRedirect:
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
                self.text = re.sub(r"\[\[(?i)" + re.escape(category.title()) + r"(\|.*)?\]\]", "", self.text, flags=re.IGNORECASE)
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
        self.source = source
        self.page_name = title
        pywikibot.Category.__init__(self, self.source.site, title)
        get_page.init_page(self)

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
        if re1 and not re2:
            return re1
        else:
            return None
    else:
        re1 = re.search(regex, text_page1)
        re2 = re.search(regex, text_page2)
        if re1 and not re2:
            return re1
        else:
            return None
