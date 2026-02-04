# -*- coding: utf-8 -*-
"""
Utilities around Pywikibot + MediaWiki API.
"""

from __future__ import annotations

import datetime
import difflib
import json
import re
import traceback
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import pywikibot
from pywikibot import pagegenerators

from config import headers


# ----------------------------
# Small helpers
# ----------------------------

def _ensure_file(path: str) -> None:
    """Create an empty file if missing (no-op otherwise)."""
    open(path, "a", encoding="utf-8").close()


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _read_lines(path: str) -> List[str]:
    _ensure_file(path)
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\r\n") for line in f.readlines()]


def _load_json_config(path: str) -> Dict[str, Any]:
    raw = _read_text(path).replace("\r", "").replace("\n", "")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.decoder.JSONDecodeError:
        pywikibot.error(f"Erreur de configuration sur {path}")
        return {}


def request_site(url: str, headers: Dict[str, str] = headers, data: Optional[bytes] = None, method: str = "GET") -> str:
    req = urllib.request.Request(url, headers=headers, data=data, method=method)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def _api_url(protocol: str, host: str, scriptpath: str, **params: Any) -> str:
    base = f"{protocol}//{host}{scriptpath}/api.php"
    params = {k: v for k, v in params.items() if v is not None}
    # Preserve original behavior: some callers already pass pre-encoded values.
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{base}?{query}" if query else base


def _paginate_json(url: str, continue_key: str) -> Iterator[Dict[str, Any]]:
    """
    Generator yielding successive JSON responses for MW API queries that paginate with `continue_key`.
    """
    cont: Optional[str] = ""
    while cont is not None:
        full_url = url + (f"&{continue_key}=" + urllib.parse.quote(cont) if cont else "")
        j = json.loads(request_site(full_url))
        yield j
        cont = j.get("continue", {}).get(continue_key)


def regex_vandalism(regex: str, text_page1: str, text_page2: str, ignorecase: bool = True):
    flags = re.IGNORECASE if ignorecase else 0
    re1 = re.search(regex, text_page1, flags)
    re2 = re.search(regex, text_page2, flags)
    return re1 if re1 and not re2 else None


def prompt_ai(lang, date, url_wiki, page_name, diff_text, comment):
    if lang == "fr":
        comment_line = f"Résumé de modification : {comment}" if comment else ""
        return f"""Analyser la modification et indiquer la probabilité que cette modification soit du vandalisme en %.
Si la modification est une révocation ou une suppression de contenu non-constructif, mettre la probabilité de vandalisme à 0 %.
Date et heure : {date}
Wiki : {url_wiki}
Page modifiée : {page_name}
Diff de la modification :
{diff_text}
{comment_line}
Format de réponse :
Analyse de la modification :
...
Probabilité de vandalisme : [probabilité] %"""
    else:
        comment_line = f"Edit summary: {comment}" if comment else ""
        return f"""Analyze the modification and indicate the probability that this edit is vandalism in %.
If the edit is a revert or a deletion of unconstructive content, set the probability of vandalism to 0%.
Date and time: {date}
Wiki: {url_wiki}
Edited page: {page_name}
Edit diff:
{diff_text}
{comment_line}
Format of answer:
Analysis of the modification:
...
Probability of vandalism: [probability] %"""

def get_warn_level(t):
    # Rough heuristic based on templates.
    has_lvl0 = any(k in t for k in ("averto-0", "niveau=0", "level=0", "avertissement-niveau-0"))
    has_lvl1 = any(k in t for k in ("averto-1", "niveau=1", "level=1", "avertissement-niveau-1"))
    has_lvl2 = any(k in t for k in ("averto-2", "niveau=2", "level=2", "avertissement-niveau-2"))

    if has_lvl2:
        warn_level = 3
    elif has_lvl1 and not has_lvl2:
        warn_level = 2
    elif has_lvl0 and not has_lvl1:
        warn_level = 1
    else:
        warn_level = 0
    return warn_level

# ----------------------------
# Public classes
# ----------------------------

class get_wiki:
    def __init__(self, family: str, lang: str, user_wiki: str):
        self.user_wiki = user_wiki
        self.family = family
        self.lang = lang

        config_filename = f"config_{family}_{lang}.txt"
        _ensure_file(config_filename)
        self.config = _load_json_config(config_filename)

        self.lang_bot = self.config.get("lang_bot", "en")
        self.days_clean_warnings = self.config.get("days_clean_warnings", 365)

        self.site = pywikibot.Site(lang, family, self.user_wiki)

        self.fullurl = self.site.siteinfo["general"]["server"]
        self.protocol = (self.fullurl.split("/")[0] or "https:")
        self.url = self.fullurl.split("/")[2]
        self.articlepath = self.site.siteinfo["general"]["articlepath"].replace("$1", "")
        self.scriptpath = self.site.siteinfo["general"]["scriptpath"]

        self.talk_page = pywikibot.Page(self.site, f"User Talk:{self.user_wiki}")

        self.trusted: List[str] = []
        self.diffs_rc: List[Dict[str, Any]] = []

    # ---- API queries

    def bot_stopped(self) -> bool:
        self.talk_page = pywikibot.Page(self.site, f"User Talk:{self.user_wiki}")
        return self.talk_page.text.lower() != "{{/stop}}"

    def get_trusted(self) -> None:
        trusted_groups = self.config.get("trusted_groups", "sysop")
        url = _api_url(
            self.protocol,
            self.url,
            self.scriptpath,
            action="query",
            list="allusers",
            augroup=trusted_groups,
            aulimit=500,
            format="json",
        )
        self.trusted = []
        for j in _paginate_json(url, "aufrom"):
            for user_info in j.get("query", {}).get("allusers", []):
                self.trusted.append(user_info.get("name", ""))

    def all_pages(
        self,
        n_pages: int = 5000,
        ns: int = 0,
        start: Optional[str] = None,
        end: Optional[str] = None,
        apfilterredir: Optional[str] = None,
        apprefix: Optional[str] = None,
        urladd: Optional[str] = None,
    ) -> List[str]:
        url = _api_url(
            self.protocol,
            self.url,
            self.scriptpath,
            action="query",
            list="allpages",
            aplimit=str(n_pages),
            apnamespace=str(ns),
            apfrom=start,
            apto=end,
            apfilterredir=apfilterredir,
            apprefix=urllib.parse.quote(apprefix) if apprefix is not None else None,
            format="json",
        )
        if urladd is not None:
            url += urllib.parse.quote(urladd)

        pages: List[str] = []
        for j in _paginate_json(url, "apcontinue"):
            for p in j.get("query", {}).get("allpages", []):
                pages.append(p.get("title", ""))
        return pages

    def problematic_redirects(self, type_redirects: str) -> List[str]:
        url = _api_url(
            self.protocol,
            self.url,
            self.scriptpath,
            action="query",
            list="querypage",
            qppage=type_redirects,
            qplimit="max",
            format="json",
        )
        pages: List[str] = []
        for j in _paginate_json(url, "apcontinue"):
            results = j.get("query", {}).get("querypage", {}).get("results", [])
            for r in results:
                pages.append(r.get("title", ""))
        return pages

    def rc_pages(
        self,
        n_edits: int = 5000,
        timestamp: Optional[str] = None,
        rctoponly: bool = True,
        show_trusted: bool = False,
        namespace: Optional[str] = None,
        timestamp_start: Optional[str] = None,
    ) -> None:
        self.diffs_rc = []
        url = _api_url(
            self.protocol,
            self.url,
            self.scriptpath,
            action="query",
            list="recentchanges",
            rclimit=str(n_edits),
            rcend=str(timestamp),
            rcprop="timestamp|title|user|ids|comment|tags",
            rctype="edit|new|categorize",
            rcshow="!bot",
            rcstart=str(timestamp_start) if timestamp_start else None,
            rcnamespace=namespace,
            format="json",
        )
        if rctoponly:
            url += "&rctoponly"

        for j in _paginate_json(url, "rccontinue"):
            for contrib in j.get("query", {}).get("recentchanges", []):
                user = contrib.get("user")
                if show_trusted or (user and user not in self.trusted):
                    self.diffs_rc.append(contrib)

    # ---- wrappers

    def page(self, page_wiki: str) -> "get_page":
        return get_page(self, page_wiki)

    def category(self, page_wiki: str) -> "get_category":
        return get_category(self, page_wiki)

    # ---- stats helper (kept as-is, but slightly cleaned)

    def add_detailed_diff_info(
        self,
        diff_info: Dict[int, Dict[str, Any]],
        page_info: Dict[str, Any],
        old: str,
        new: str,
        vandalism_score: int,
    ) -> Dict[int, Dict[str, Any]]:
        revid = page_info["revid"]
        entry = diff_info.setdefault(revid, {"reverted": False, "next_revid": -1})
        entry.update(
            {
                "score": vandalism_score,
                "anon": "anon" in page_info,
                "trusted": ("user" in page_info and page_info["user"] in self.trusted),
                "user": page_info.get("user", ""),
                "page": page_info.get("title", ""),
                "old": old,
                "new": new,
            }
        )

        # Heuristic: consider a series of edits by the same user as reverted if the next revision got reverted.
        if not entry["reverted"]:
            next_id = entry.get("next_revid", -1)
            if (
                next_id > 0
                and not entry["trusted"]
                and diff_info.get(next_id, {}).get("reverted")
                and page_info.get("user")
                and diff_info.get(next_id, {}).get("user") == page_info.get("user")
            ):
                entry["reverted"] = True

        old_revid = page_info.get("old_revid", 0)
        if old_revid not in (0, -1):
            prev = diff_info.setdefault(old_revid, {"reverted": False, "next_revid": revid})
            comment = page_info.get("comment", "").lower()
            if comment:
                prev["reverted"] = any(k in comment for k in ("revert", "révoc", "cancel", "annul"))
        return diff_info


class get_page(pywikibot.Page):
    def __init__(self, source: get_wiki, title: str):
        self.source = source
        self.user_wiki = source.user_wiki
        self.lang = source.lang
        self.lang_bot = source.lang_bot

        self.page_name = title
        prefix = (self.page_name.split(":")[0] if ":" in self.page_name else "").lower()
        self.special = prefix in {"special", "spécial"}

        if not self.special:
            super().__init__(self.source.site, self.page_name)

        self.new_page: Optional[bool] = None
        self.text_page_oldid: Optional[str] = None
        self.text_page_oldid2: Optional[str] = None
        self.vandalism_score_detect: List[List[Any]] = []
        self.vand_to_revert = False
        self.reverted = False
        self.list_contributor_rights = None

        fullurl = self.source.site.siteinfo["general"]["server"] + self.source.site.siteinfo["general"]["articlepath"].replace("$1", self.page_name)
        self.protocol = (fullurl.split("/")[0] or "https:")
        self.url = fullurl.split("/")[2]
        self.articlepath = self.source.site.siteinfo["general"]["articlepath"].replace("$1", "")
        self.scriptpath = self.source.site.siteinfo["general"]["scriptpath"]

        if not self.special:
            try:
                self.contributor_name = self.latest_revision.user
                self.page_ns = self.namespace()
                self.oldid = self.latest_revision_id
                self.size = len(self.text)
            except Exception:
                self.contributor_name = ""
                self.page_ns = -1
                self.oldid = None
                self.size = None

        # thresholds
        self.limit = self.source.config.get("limit", -20)
        self.limit2 = self.source.config.get("limit2", -10)
        self.limit_ai = self.source.config.get("limit_ai", 98)
        self.limit_ai2 = self.source.config.get("limit_ai2", 90)
        self.limit_ai3 = self.source.config.get("limit_ai3", 50)

        # alert page
        alert_page_tpl = self.source.config.get("alert_page")
        if alert_page_tpl:
            self.alert_page = datetime.datetime.now().strftime(alert_page_tpl.replace("\r", "").replace("\n", ""))
        else:
            self.alert_page = "Project:Alerte" if self.lang_bot == "fr" else "Project:Alert"

        self.alert_request = False
        self.warn_level = -1

    # ---- revert + warnings

    def revert(self, summary: str = "", test = False, result_regex = "", result_ai = "") -> None:
        if test:
            if result_regex != "":
                field_regex = f"""* Détection (expressions rationnelles) :
<pre>
{result_regex}
</pre>"""
            else:
                field_regex = ""
            if result_ai != "":
                field_ai = f"""* Détection de l'IA :
<pre>
{result_ai}
</pre>"""
            else:
                field_ai = ""
            test_page = pywikibot.Page(self.source.site, f"User:{self.user_wiki}/Tests")
            test_page.text = f"""{test_page.text}
== Vandalisme détecté (diff : {self.oldid}) ==
* Page : {self.page_name}
* Utilisateur : {self.contributor_name}
* Diff : [[Special:Diff/{self.oldid}]]
* {summary}
{field_regex}
{field_ai}"""
            test_page.save("Ajout vandalisme", bot=False, minor=False)
        else:
            self.only_revert(summary)
            self.warn_revert(summary)

    def only_revert(self, summary: str = "") -> None:
        if self.text_page_oldid is None or self.text_page_oldid2 is None:
            self.get_text_page_old()

        self.text = "{{subst:User:%s/VandalismDelete}}" % self.user_wiki if self.new_page else (self.text_page_oldid2 or "")

        if self.lang_bot == "fr":
            msg = ("Annulation : " + summary) if summary else "Annulation modification non-constructive"
        else:
            msg = ("Revert : " + summary) if summary else "Revert"
        self.save(msg, bot=False, minor=False)
        self.reverted = True

    def get_warnings_user(self) -> None:
        self.talk = pywikibot.Page(self.source.site, f"User Talk:{self.contributor_name}")
        t = self.talk.text.lower()
        self.warn_level = get_warn_level(t)

    def warn_revert(self, summary: str = "") -> None:
        if self.warn_level < 0:
            self.get_warnings_user()

        if self.warn_level >= 2:
            alert = pywikibot.Page(self.source.site, self.alert_page)
            alert.text += f"\n{{{{subst:User:{self.user_wiki}/Alert|{self.contributor_name}}}}}"
            alert.save("Alerte vandalisme" if self.lang_bot == "fr" else "Vandalism alert", bot=False, minor=False)

            self.talk.text += f"\n{{{{subst:User:{self.user_wiki}/Vandalism2|{self.page_name}|{summary}}}}} <!-- level=2 -->"
            self.talk.save("Avertissement 2" if self.lang_bot == "fr" else "Warning 2", bot=False, minor=False)
            self.alert_request = True

        elif self.warn_level == 1:
            self.talk.text += f"\n{{{{subst:User:{self.user_wiki}/Vandalism1|{self.page_name}|{summary}}}}} <!-- level=1 -->"
            self.talk.save("Avertissement 1" if self.lang_bot == "fr" else "Warning 1", bot=False, minor=False)

        else:
            self.talk.text += f"\n{{{{subst:User:{self.user_wiki}/Vandalism0|{self.page_name}|{summary}}}}} <!-- level=0 -->"
            self.talk.save("Avertissement 0" if self.lang_bot == "fr" else "Warning 0", bot=False, minor=False)

    # ---- vandalism scoring

    def vandalism_get_score_current(self) -> int:
        """Score on current revision, ignoring experienced contributors."""
        if self.contributor_is_trusted():
            return 0

        user_rights = self.contributor_rights()
        vand = self.vandalism_score()

        if vand <= self.limit and "autoconfirmed" not in user_rights:
            self.vand_to_revert = True
        elif vand <= self.limit2 and "autoconfirmed" not in user_rights:
            self.get_warnings_user()
            self.vand_to_revert = self.warn_level > 0
        else:
            self.vand_to_revert = False
        return vand

    def contributor_is_trusted(self) -> bool:
        return (
            self.contributor_name == self.user_wiki
            or self.contributor_name in self.source.trusted
            or (self.page_ns == 2 and self.contributor_name in self.page_name)
        )

    def contributor_rights(self) -> List[str]:
        if self.list_contributor_rights is None:
            url = _api_url(
                self.protocol,
                self.url,
                self.scriptpath,
                action="query",
                list="users",
                ususers=urllib.parse.quote(self.contributor_name),
                usprop="rights",
                format="json",
            )
            j = json.loads(request_site(url))
            self.list_contributor_rights = j.get("query", {}).get("users", [{}])[0].get("rights", []) or []
        return self.list_contributor_rights

    def get_text_page_old(self, revision_oldid: Optional[int] = None, revision_oldid2: Optional[int] = None) -> None:
        """
        revision_oldid: new version / version to check
        revision_oldid2: old version / version to compare against
        """
        if revision_oldid is not None:
            text_new = self.getOldVersion(oldid=revision_oldid)
        else:
            text_new = self.text

        oldid = revision_oldid2 if revision_oldid2 is not None else -1

        if oldid is None or oldid == -1:
            try:
                for rev in self.revisions():
                    if rev.user != self.contributor_name and (revision_oldid is None or rev.revid <= revision_oldid):
                        oldid = rev.revid
                        break
            except Exception:
                oldid = -1

        if oldid not in (-1, 0):
            self.new_page = False
            text_old = self.getOldVersion(oldid=oldid)
        else:
            self.new_page = True
            text_old = ""

        self.text_page_oldid = text_new or ""
        self.text_page_oldid2 = text_old or ""

    def get_diff(self) -> str:
        diff = difflib.unified_diff((self.text_page_oldid2 or "").splitlines(), (self.text_page_oldid or "").splitlines())
        return "\n".join(diff)

    def is_revert(self) -> bool:
        return any(tag in self.latest_revision.tags for tag in ("mw-undo", "mw-rollback", "mw-manual-revert")) \
            or any(k in self.latest_revision.comment for k in ("revert", "révoc", "cancel", "annul"))

    @staticmethod
    def _parse_scored_lines(lines: Iterable[str]) -> List[Tuple[str, int]]:
        out: List[Tuple[str, int]] = []
        for line in lines:
            if not line or ":" not in line:
                continue
            key, score_s = line.rsplit(":", 1)
            key = key.strip()
            try:
                score = int(score_s.strip())
            except ValueError:
                continue
            out.append((key, score))
        return out

    def vandalism_score(self, revision_oldid: Optional[int] = None, revision_oldid2: Optional[int] = None) -> int:
        """Score on a diff, including experienced users."""
        self.get_text_page_old(revision_oldid, revision_oldid2)

        fam, lang = self.source.family, self.lang
        files = {
            "add_regex_ns_all": f"regex_vandalisms_all_{fam}_{lang}.txt",
            "add_regex": f"regex_vandalisms_0_{fam}_{lang}.txt",
            "add_regex_no_ignore_case": f"regex_vandalisms_0_{fam}_{lang}_no_ignore_case.txt",
            "add_regex_lines_no_ignore_case": f"regex_vandalisms_lines_0_{fam}_{lang}_no_ignore_case.txt",
            "del_regex_lines": f"regex_vandalisms_del_lines_0_{fam}_{lang}.txt",
            "size": f"size_vandalisms_0_{fam}_{lang}.txt",
            "diff": f"diff_vandalisms_0_{fam}_{lang}.txt",
        }
        for f_type in files:
            _ensure_file(files[f_type])

        vand = 0
        text_new = self.text_page_oldid or ""
        text_old = self.text_page_oldid2 or ""
        unified_diff = difflib.unified_diff(text_old.splitlines(), text_new.splitlines(), lineterm="")

        old_lines_edited = []
        new_lines_edited = []

        for line in unified_diff:
            if line.startswith("-") and not line.startswith("---"):
                old_lines_edited.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                new_lines_edited.append(line[1:])

        old_lines_edited_join = "\r\n".join(old_lines_edited)
        new_lines_edited_join = "\r\n".join(new_lines_edited)

        for pattern, score in self._parse_scored_lines(_read_lines(files["add_regex_ns_all"])):
            hit = regex_vandalism(pattern, text_new, text_old)
            if hit:
                self.vandalism_score_detect.append(["add_regex_ns_all", score, hit])
                vand += score

        if self.page_ns == 0:
            # add regex
            for pattern, score in self._parse_scored_lines(_read_lines(files["add_regex"])):
                hit = regex_vandalism(pattern, text_new, text_old)
                if hit:
                    self.vandalism_score_detect.append(["add_regex", score, hit])
                    vand += score
    
            # add regex (don't ignore case)
            for pattern, score in self._parse_scored_lines(_read_lines(files["add_regex_no_ignore_case"])):
                hit = regex_vandalism(pattern, text_new, text_old, False)
                if hit:
                    self.vandalism_score_detect.append(["add_regex_no_ignore_case", score, hit])
                    vand += score

            # add regex (don't ignore case)
            for pattern, score in self._parse_scored_lines(_read_lines(files["add_regex_lines_no_ignore_case"])):
                hit = regex_vandalism(pattern, new_lines_edited_join, old_lines_edited_join, False)
                if hit:
                    self.vandalism_score_detect.append(["add_regex_lines_no_ignore_case", score, hit])
                    vand += score
    
            # size rules
            for size_s, score in self._parse_scored_lines(_read_lines(files["size"])):
                try:
                    size = int(size_s)
                except ValueError:
                    continue
                if len(text_new) < size:
                    self.vandalism_score_detect.append(["size", score, size_s])
                    vand += score
    
            # diff rules
            for diff_s, score in self._parse_scored_lines(_read_lines(files["diff"])):
                try:
                    d = int(diff_s)
                except ValueError:
                    continue
                delta = len(text_new) - len(text_old)
                if (d < 0 and delta <= d) or (d >= 0 and delta >= d):
                    self.vandalism_score_detect.append(["diff", score, diff_s])
                    vand += score
    
            # delete regex (pattern removed between old->new)
            for pattern, score in self._parse_scored_lines(_read_lines(files["del_regex_lines"])):
                hit = regex_vandalism(pattern, old_lines_edited_join, new_lines_edited_join)
                if hit:
                    self.vandalism_score_detect.append(["del_regex_lines", score, hit])
                    vand += score

        return vand

    def get_vandalism_report(self) -> str:
        detected_lines: List[str] = []
        for kind, score, payload in self.vandalism_score_detect:
            if kind == "add_regex_ns_all" or kind == "add_regex" or kind == "add_regex_no_ignore_case":
                detected_lines.append(f"{score} - + {payload.group()}")
            elif kind == "add_regex_lines_no_ignore_case":
                detected_lines.append(f"{score} - + {payload.group()} (diff)")
            elif kind == "del_regex_lines":
                detected_lines.append(f"{score} - - {payload.group()} (diff)")
            elif kind == "size":
                detected_lines.append(f"{score} - size < {payload}")
            elif kind == "diff":
                op = ">" if int(payload) > 0 else "<"
                detected_lines.append(f"{score} - diff {op} {payload}")
            else:
                detected_lines.append(f"{score} - + {payload.group()}")
        return "\n".join(detected_lines)

    # ---- other tools

    def check_WP(self, page_name_WP: Optional[str] = None, diff: Optional[int] = None, lang: Optional[str] = None) -> int:
        page_name_WP = page_name_WP or self.page_name
        text_to_check = (self.text.strip() if diff is None else (self.getOldVersion(oldid=diff) or "")).strip()
        lang = lang or self.lang_bot

        url = _api_url(
            "https:",
            f"{lang}.wikipedia.org",
            "/w",
            action="query",
            prop="revisions",
            rvprop="content",
            rvslots="*",
            titles=urllib.parse.quote(page_name_WP),
            formatversion=2,
            format="json",
        )
        j = json.loads(request_site(url))
        if "missing" in j.get("query", {}).get("pages", [{}])[0]:
            return 0

        page_text_WP = j["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
        matcher = difflib.SequenceMatcher(a=text_to_check, b=page_text_WP)
        score = sum(m.size for m in matcher.get_matching_blocks())

        return self.check_WP(page_name_WP, diff, "simple") if score < 10 and lang == "en" else score

    def edit_replace(self) -> int:
        file1 = f"replace1_{self.source.family}_{self.lang}.txt"
        file2 = f"replace2_{self.source.family}_{self.lang}.txt"
        _ensure_file(file1)
        _ensure_file(file2)

        patterns = _read_lines(file1)
        repls = _read_lines(file2)

        text_page = self.text
        n = 0
        for i, pat in enumerate(patterns):
            if i >= len(repls):
                break
            rep = repls[i]
            pywikibot.output(f"Remplacement du regex {pat} par {rep}...")
            new_text = re.sub(pat, rep, text_page)
            if new_text != text_page:
                n += 1
                text_page = new_text
                pywikibot.output(f"Le regex {pat} a été trouvé et va être remplacé par {rep}.")

        if n:
            self.text = text_page
            self.save(f"{n} recherches-remplacements" if self.lang_bot == "fr" else f"{n} find-replaces")
            pywikibot.output(f"{n} recherches-remplacements effectuées ({self})")
        else:
            pywikibot.output("Rien à remplacer.")
        return n

    def redirects(self) -> None:
        try:
            target = self.getRedirectTarget()

            if not target.exists():
                self._request_redirect_delete(circular=False)
                return

            if target.isRedirectPage():
                self._fix_double_redirect(target)
                return

            pywikibot.output("Redirection correcte.")

        except pywikibot.exceptions.CircularRedirectError:
            self._request_redirect_delete(circular=True)

    def _request_redirect_delete(self, circular: bool) -> None:
        try:
            if self.lang_bot == "fr":
                tpl = f"{{{{User:{self.user_wiki}/RedirectDelete|circular=True}}}}" if circular else f"{{{{User:{self.user_wiki}/RedirectDelete}}}}"
                msg = "Demande suppression redirection en boucle" if circular else "Demande suppression redirection cassée"
            else:
                tpl = f"{{{{User:{self.user_wiki}/RedirectDelete|circular=True}}}}" if circular else f"{{{{User:{self.user_wiki}/RedirectDelete}}}}"
                msg = "Delete circular redirect" if circular else "Delete broken redirect"

            self.put(tpl, msg)
            pywikibot.output("Redirecton en boucle demandée à la suppression." if circular else "Redirecton cassée demandée à la suppression.")
        except Exception:
            try:
                pywikibot.error(traceback.format_exc())
            except UnicodeError:
                pass

    def _fix_double_redirect(self, target: pywikibot.Page) -> None:
        try:
            final = target.getRedirectTarget().title()
            msg = "Correction redirection" if self.lang_bot == "fr" else "Correct redirect"
            self.put(f"#REDIRECT[[{final}]]", msg)
            pywikibot.output("Double redirection corrigée.")
        except Exception:
            try:
                pywikibot.error(traceback.format_exc())
            except UnicodeError:
                pass

    def category_page(self, category_name: str) -> bool:
        return any(cat.title() == category_name for cat in self.categories())

    def del_categories_no_exists(self) -> List[str]:
        removed: List[str] = []
        for cat in self.categories():
            if not cat.exists():
                self.text = re.sub(r"(?i)\[\[" + re.escape(cat.title()) + r"(\|.*)?\]\]", "", self.text, flags=re.IGNORECASE)
                removed.append(cat.title())

        if removed:
            self.save("Suppression des catégories inexistantes" if self.lang_bot == "fr" else "Deleting non-existent categories")
        return removed

    def del_files_no_exists(self) -> List[str]:
        removed: List[str] = []
        for file_page in self.imagelinks():
            if not file_page.exists():
                self.text = re.sub(r"\[\[(?i)" + re.escape(file_page.title()) + r"(\|.*)?\]\]", "", self.text, flags=re.IGNORECASE)
                removed.append(file_page.title())

        if removed:
            self.save("Suppression des fichiers inexistantes")
        return removed


class get_category(get_page, pywikibot.Category):
    def __init__(self, source: get_wiki, title: str):
        pywikibot.Category.__init__(self, source.site, title)
        get_page.__init__(self, source, title)

    def cat_pages(self) -> int:
        return sum(1 for _ in pagegenerators.CategorizedPageGenerator(self))

    def get_pages(self, ns: Optional[int] = None) -> List[str]:
        pages: List[str] = []
        for page in pagegenerators.CategorizedPageGenerator(self):
            if ns is None or page.namespace() == ns:
                pages.append(page.title())
        return pages
