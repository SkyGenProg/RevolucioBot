# -*- coding: utf-8 -*-
"""
Scheduled tasks for the wiki bot.
"""

from __future__ import annotations

import datetime
import json
import re
import time
import traceback
from typing import Any, Dict, List, Optional

import pywikibot
from mistralai import Mistral

from config import api_key, headers, model, webhooks_url, webhooks_url_ai
from includes.wiki import request_site, prompt_ai

client = Mistral(api_key=api_key)

def _safe_log_exc() -> None:
    try:
        pywikibot.error(traceback.format_exc())
    except UnicodeError:
        pass


def _send_webhook(url: Optional[str], payload: Dict[str, Any]) -> None:
    if not url:
        return
    request_site(url, headers, json.dumps(payload).encode("utf-8"), "POST")


def _send_embed_chunked(url: Optional[str], embed_base: Dict[str, Any], text: str, chunk_size: int = 4096) -> None:
    if not url:
        return
    if not text:
        _send_webhook(url, {"embeds": [embed_base]})
        return
    for i in range(len(text) // chunk_size + 1):
        chunk = text[chunk_size * i : chunk_size * (i + 1)]
        if not chunk:
            continue
        embed = dict(embed_base)
        embed["description"] = chunk
        _send_webhook(url, {"embeds": [embed]})


class wiki_task:
    def __init__(self, site, start_task_day: bool = False, start_task_month: bool = False, ignore_task_month: bool = False):
        self.site = site
        self.start_task_day = start_task_day
        self.start_task_month = start_task_month and not ignore_task_month
        self.ignore_task_month = ignore_task_month
        self.site.get_trusted()  # récupération des utilisateurs ignorés par le bot

        self.datetime_utcnow = datetime.datetime.utcnow()

    def send_message_bot_stopped(self) -> None:
        if self.site.lang_bot == "fr":
            title = "Bot arrêté"
            desc = "Un utilisateur a arrêté le bot."
        else:
            title = "Bot stopped"
            desc = "An user stopped the bot."
        _send_webhook(webhooks_url[self.site.family], {"embeds": [{"title": title, "description": desc, "color": 13371938}]})

    # ----------------------------
    # Monthly / daily / periodic
    # ----------------------------

    def task_every_month(self) -> None:
        pywikibot.output(f"Tâches mensuelles ({self.site.family} {self.site.lang}).")

        if self.site.config.get("check_all_pages"):
            for page_name in self.site.all_pages(ns=0):
                page = self.site.page(page_name)
                pywikibot.output("Page : " + page_name)

                if not self.site.config.get("disable_vandalism", False):
                    self.check_vandalism(page)

                edit_replace = page.edit_replace()
                pywikibot.output(f"{edit_replace} recherche(s)-remplacement(s) sur la page {page}.")

                if not self.site.config.get("disable_del_categories", False) and page.page_ns != 2:
                    pywikibot.output("Suppression des catégories inexistantes sur la page " + str(page))
                    removed = page.del_categories_no_exists()
                    pywikibot.output("Catégories retirées " + ", ".join(removed) if removed else "Aucune catégorie à retirer.")

                if self.site.family == "dicoado":
                    self._dicoado_maintenance(page_name, page)

        if self.site.config.get("clear_talks"):
            self._clear_ip_talks()

    def task_every_day(self) -> None:
        # Correction redirections une fois par jour
        if self.site.config.get("correct_redirects"):
            for page_name in (self.site.problematic_redirects("DoubleRedirects") + self.site.problematic_redirects("BrokenRedirects")):
                page = self.site.page(page_name)
                if page.isRedirectPage():
                    pywikibot.output("Correction de redirection sur la page " + str(page))
                    page.redirects()
        self.task_every_10minutes(task_day=True)

    def task_every_10minutes(self, task_day: bool = False) -> None:
        detailed_diff_info: Dict[int, Dict[str, Any]] = {}

        if task_day:
            pywikibot.output(f"Tâches réalisées tous les jours ({self.site.family} {self.site.lang}).")
            since = self.datetime_utcnow - datetime.timedelta(hours=24)
            pywikibot.output(f"Récupération des RC des 24 dernières heures sur {self.site.family} {self.site.lang}...")
            self.site.rc_pages(timestamp=since.strftime("%Y%m%d%H%M%S"), rctoponly=False, show_trusted=True)
        else:
            pywikibot.output(f"Tâches réalisées une fois toutes les 10 minutes ({self.site.family} {self.site.lang}).")
            since = self.datetime_utcnow - datetime.timedelta(minutes=10)
            pywikibot.output(f"Récupération des RC des 10 dernières minutes sur {self.site.family} {self.site.lang}...")
            self.site.rc_pages(timestamp=since.strftime("%Y%m%d%H%M%S"))

        pages_checked: set[str] = set()

        for page_info in self.site.diffs_rc:
            try:
                page_name = page_info["title"]
                page = self.site.page(page_name)

                if page.special or not page.exists():
                    continue

                pywikibot.output("Page : " + page_name)

                is_redirect = page.isRedirectPage()
                if task_day and not is_redirect:
                    try:
                        self.vandalism_score = page.vandalism_score(page_info["revid"], page_info["old_revid"])
                        detailed_diff_info = self.site.add_detailed_diff_info(
                            detailed_diff_info, page_info, page.text_page_oldid, page.text_page_oldid2, self.vandalism_score
                        )
                    except Exception:
                        _safe_log_exc()

                if page_name in pages_checked:
                    continue
                pages_checked.add(page_name)

                if is_redirect:
                    if self.site.config.get("correct_redirects"):
                        pywikibot.output("Correction de redirection sur la page " + str(page))
                        page.redirects()
                    else:
                        pywikibot.output(f"La page {page} est une redirection.")
                    continue

                is_revert = page.is_revert()

                if not is_revert and not self.site.config.get("disable_vandalism", False):
                    self.check_vandalism(page)

                if not is_revert and not self.site.config.get("disable_ai", False):
                    self.check_vandalism_ai(page)

                if page.page_ns == 0:
                    if self.site.config.get("check_WP") and page.text.strip():
                        self.check_WP(page)

                    edit_replace = page.edit_replace()
                    pywikibot.output(f"{edit_replace} recherche(s)-remplacement(s) sur la page {page}.")

                if task_day and (not self.site.config.get("disable_del_categories", False)) and page.page_ns != 2:
                    pywikibot.output("Suppression des catégories inexistantes sur la page " + str(page))
                    try:
                        removed = page.del_categories_no_exists()
                        pywikibot.output("Catégories retirées " + ", ".join(removed) if removed else "Aucune catégorie à retirer.")
                    except Exception:
                        _safe_log_exc()

            except Exception:
                _safe_log_exc()

        if task_day:
            self.site.get_trusted()
            self._daily_stats_and_webhook(detailed_diff_info, since)

        if self.site.family == "dicoado":
            self._dicoado_sandbox_reset()

    # ----------------------------
    # Maintenance helpers
    # ----------------------------

    def _dicoado_maintenance(self, page_name: str, page) -> None:
        try:
            if page.isRedirectPage():
                return

            original = page.text

            def _field_edit(field_base: str, i: int, transform):
                n = "" if i == 1 else str(i)
                field = f"|{field_base}{n}="
                if field not in page.text:
                    return
                try:
                    parts = page.text.split(field, 1)
                    rhs = parts[1]
                    split_token = "=" if "=" in rhs else "}}"
                    before, after = rhs.split(split_token, 1)
                    before = transform(before)
                    parts[1] = split_token.join([before, after])
                    page.text = field.join(parts)
                except Exception:
                    _safe_log_exc()

            def _bold_title(s: str) -> str:
                s = re.sub(r"(\s|[=#'])(?!'{3,})\b(" + re.escape(page_name) + r")(\w{0,})\b(?!'{3,})", r"\1'''\2\3'''", s)
                return re.sub(r'\B(?!{{\"\|)\"\b([^\"]*)\b\"(?!}})\B', r'{{"|\1}}', s)

            def _capitalize_first(s: str) -> str:
                return s[:1].upper() + s[1:] if s else s

            def _lower_first(s: str) -> str:
                return s[:1].lower() + s[1:] if s else s

            for i in range(1, 5):
                _field_edit("ex", i, lambda s: _capitalize_first(_bold_title(s)))
                _field_edit("contr", i, lambda s: s.replace("[[", "").replace("]]", ""))
                _field_edit("syn", i, lambda s: s.replace("[[", "").replace("]]", ""))
                _field_edit("voir", i, lambda s: s.replace("[[", "").replace("]]", ""))
                _field_edit("def", i, lambda s: re.sub(r'\B(?!{{\"\|)\"\b([^\"]*)\b\"(?!}})\B', r'{{"|\1}}', _lower_first(s)))

            if "|son=LL-Q150" in page.text:
                page.text = page.text.replace("|son=LL-Q150", "|prononciation=LL-Q150")

            if page.text != original:
                page.save("maintenance")

        except Exception:
            _safe_log_exc()

    def _clear_ip_talks(self) -> None:
        for page_name in self.site.all_pages(ns=3, start="1", end="A"):
            pywikibot.output("Page : " + page_name)

            is_ip_title = (page_name.count(".") == 3) or (page_name.count(":") == 8)
            if not is_ip_title:
                pywikibot.output("Pas une PDD d'IP")
                continue

            user_talk = pywikibot.User(self.site.site, ":".join(page_name.split(":")[1:]))
            if not user_talk.isAnonymous():
                pywikibot.output("Pas une PDD d'IP")
                continue

            page = self.site.page(page_name)
            pywikibot.output("PDD d'IP")

            too_old = abs((self.datetime_utcnow - page.latest_revision.timestamp).days) > self.site.days_clean_warnings

            if page.page_ns == 3 and too_old:
                pywikibot.output("Suppression des avertissements de la page " + page_name)
                try:
                    if self.site.lang_bot == "fr":
                        page.put("{{Avertissement effacé|{{subst:#time: j F Y}}}}", "Anciens messages effacés", minor=False)
                    else:
                        page.put("{{Warning cleared|{{subst:#time: j F Y}}}}", "Old messages cleared", minor=False)
                except Exception:
                    _safe_log_exc()
            else:
                pywikibot.output("Pas d'avertissement à effacer")

    def _dicoado_sandbox_reset(self) -> None:
        bas = self.site.page("Dico:Bac à sable")
        bas_zero = self.site.page("Dico:Bac à sable/Zéro")

        if abs((self.datetime_utcnow - bas.latest_revision.timestamp).seconds) > 3600 and bas.text != bas_zero.text:
            pywikibot.output("Remise à zéro du bac à sable")
            bas.put(bas_zero.text, "Remise à zéro du bac à sable")

        for page_name in self.site.all_pages(ns=4, apprefix="Bac à sable/Test/"):
            if page_name == "Dico:Bac à sable/Zéro":
                continue
            bas_page = self.site.page(page_name)
            if abs((self.datetime_utcnow - bas_page.latest_revision.timestamp).seconds) > 7200 and "{{SI" not in bas_page.text:
                pywikibot.output("SI de " + page_name)
                bas_page.text = "{{SI|Remise à zéro du bac à sable}}\n" + bas_page.text
                bas_page.save("Remise à zéro du bac à sable")

    # ----------------------------
    # Vandalism detection (non-AI)
    # ----------------------------

    def check_vandalism(self, page, test = False) -> None:
        page_name = page.page_name
        self.vandalism_score = page.vandalism_get_score_current()

        detected_lines: List[str] = []
        for kind, score, payload in getattr(page, "vandalism_score_detect", []):
            if kind == "add_regex":
                detected_lines.append(f"{score} - + {payload.group()}")
            elif kind == "del_regex":
                detected_lines.append(f"{score} - - {payload.group()}")
            elif kind == "size":
                detected_lines.append(f"{score} - size = {page.size} < {payload}")
            elif kind == "diff":
                op = ">" if int(payload) > 0 else "<"
                detected_lines.append(f"{score} - diff {op} {payload}")
            else:
                detected_lines.append(f"{score} - + {payload.group()}")

        detected = "\n".join(detected_lines)

        if page.vand_to_revert:
            page.revert(
                f"Modification non-constructive détectée par expressions rationnelles (score : {self.vandalism_score})"
                if self.site.lang_bot == "fr"
                else f"Unconstructive edit reverted by regex (score: {self.vandalism_score})",
                test,
                result_regex=detected
            )

        if self.vandalism_score < 0 and webhooks_url.get(self.site.family):
            if not test and page.vand_to_revert:
                title = (
                    f"Modification non-constructive révoquée sur {self.site.lang}:{page_name}"
                    if self.site.lang_bot == "fr"
                    else f"Unconstructive edit reverted on {self.site.lang}:{page_name}"
                )
                description = (
                    "Cette modification a été détectée comme non-constructive"
                    if self.site.lang_bot == "fr"
                    else "This edit has been detected as unconstructive"
                )
                color = 13371938
            elif self.vandalism_score <= page.limit2:
                title = (
                    f"Modification suspecte sur {self.site.lang}:{page_name}"
                    if self.site.lang_bot == "fr"
                    else f"Edit maybe unconstructive on {self.site.lang}:{page_name}"
                )
                description = (
                    "Cette modification est probablement non-constructive"
                    if self.site.lang_bot == "fr"
                    else "This edit is probably unconstructive"
                )
                color = 12138760
            else:
                title = (
                    f"Modification à vérifier sur {self.site.lang}:{page_name}"
                    if self.site.lang_bot == "fr"
                    else f"Edit to verify on {self.site.lang}:{page_name}"
                )
                description = (
                    "Cette modification est peut-être non-constructive"
                    if self.site.lang_bot == "fr"
                    else "This edit is maybe unconstructive"
                )
                color = 12161032

            fields = [
                {"name": "Score", "value": str(self.vandalism_score), "inline": True},
            ]

            embed_base = {
                "title": title,
                "description": description,
                "url": page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                "author": {"name": page.contributor_name},
                "color": color,
                "fields": fields,
            }

            _send_webhook(webhooks_url[self.site.family], {"embeds": [embed_base]})
            _send_embed_chunked(webhooks_url[self.site.family], {k: v for k, v in embed_base.items() if k != "fields"}, detected)

        if not test and webhooks_url.get(self.site.family) and page.alert_request:
            self.block_alert(page)

    # ----------------------------
    # Vandalism detection (AI)
    # ----------------------------

    def check_vandalism_ai(self, page, test = False) -> None:
        if page.contributor_is_trusted():
            return

        diff_text = page.get_diff()
        prompt = prompt_ai(self.site.lang_bot, page.latest_revision.timestamp, page.url, page.page_name, diff_text, page.latest_revision.comment)
        if self.site.lang_bot == "fr":
            proba_re = r"probabilité de vandalisme.*:[^0-9]*([\d\.,]+)[^0-9]*%"
            title_base = f"Analyse de l'IA (Mistral) sur {self.site.lang}:{page.page_name}"
            fail_title = f"Analyse de l'IA (Mistral) échouée sur {self.site.lang}:{page.page_name}"
        else:
            proba_re = r"probability of vandalism.*:[^0-9]*([\d\.,]+)[^0-9]*%"
            title_base = f"AI analysis (Mistral) on {self.site.lang}:{page.page_name}"
            fail_title = f"AI analysis (Mistral) failed on {self.site.lang}:{page.page_name}"

        try:
            chat_response = client.chat.complete(model=model, messages=[{"role": "user", "content": prompt}])
            result_ai = chat_response.choices[0].message.content
        except Exception:
            _safe_log_exc()
            embed = {
                "title": fail_title,
                "description": "",
                "url": page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                "author": {"name": page.contributor_name},
                "color": 13371938,
            }
            _send_webhook(webhooks_url_ai.get(self.site.family), {"embeds": [embed]})
            if webhooks_url.get(self.site.family) and page.alert_request:
                self.block_alert(page)
            return

        m = re.search(proba_re, result_ai.lower())
        self.proba_ai = float(m.group(1).replace(",", ".")) if m else 0.0

        user_rights = page.contributor_rights()

        if self.proba_ai >= page.limit_ai and "autoconfirmed" not in user_rights:
            if not page.reverted:
                page.revert(f"Modification non-constructive détectée par IA à {self.proba_ai} %" if self.site.lang_bot == "fr" else f"Non-constructive edit detected by AI ({self.proba_ai} %)", test, result_ai)
            color = 13371938
        elif self.proba_ai >= page.limit_ai2 and "autoconfirmed" not in user_rights:
            page.get_warnings_user()
            if page.warn_level > 0 and not page.reverted:
                page.revert(f"Modification non-constructive détectée par IA à {self.proba_ai} %" if self.site.lang_bot == "fr" else f"Non-constructive edit detected by AI ({self.proba_ai} %)", test, result_ai)
                color = 13371938
            else:
                color = 12138760
        elif self.proba_ai >= page.limit_ai3:
            color = 12138760
        else:
            color = 12161032

        title = title_base + (" (modification révoquée)" if (self.site.lang_bot == "fr" and page.reverted) else "")
        title = title + (" (reverted edit)" if (self.site.lang_bot != "fr" and page.reverted) else "")

        embed_base = {
            "title": title,
            "description": "",
            "url": page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
            "author": {"name": page.contributor_name},
            "color": color,
        }
        _send_embed_chunked(webhooks_url_ai.get(self.site.family), embed_base, result_ai)

        if not test and webhooks_url.get(self.site.family) and page.alert_request:
            self.block_alert(page)

    # ----------------------------
    # Alerts / copy detection / stats
    # ----------------------------

    def block_alert(self, page) -> None:
        if self.site.lang_bot == "fr":
            title = "Demande de blocage de " + page.contributor_name
            desc = "Un vandale est à bloquer."
        else:
            title = "Request to block against " + page.contributor_name
            desc = "A vandal must be blocked."

        embed = {
            "title": title,
            "description": desc,
            "url": page.protocol + "//" + page.url + page.articlepath + page.alert_page.replace(" ", "_"),
            "author": {"name": page.contributor_name},
            "color": 16711680,
        }
        _send_webhook(webhooks_url.get(self.site.family), {"embeds": [embed]})

    def check_WP(self, page) -> None:
        page_name = page.page_name
        score_check_WP = page.check_WP()
        prob_WP = score_check_WP / len(page.text.strip()) * 100
        template_WP = "User:" + page.user_wiki + "/CopyWP"

        pywikibot.output(
            f"Probabilité de copie de Wikipédia de la page {page} : {prob_WP} % ({score_check_WP} octets en commun/{len(page.text.strip())} octets))"
        )

        def _embed(title: str, desc: str, color: int) -> Dict[str, Any]:
            return {
                "title": title,
                "description": desc,
                "url": page.protocol + "//" + page.url + page.articlepath + "index.php?diff=prev&oldid=" + str(page.oldid),
                "author": {"name": page.contributor_name},
                "color": color,
                "fields": [{"name": ("Probabilité de copie" if self.site.lang_bot == "fr" else "Probability of copy"), "value": f"{round(prob_WP, 2)} %", "inline": True}],
            }

        if prob_WP >= 90:
            if template_WP not in page.text:
                page.text = "{{" + template_WP + "|" + page_name + "|" + str(round(prob_WP, 2)) + "}}\n" + page.text
                page.save("copie de WP" if self.site.lang_bot == "fr" else "copy of WP", bot=False, minor=False)

            embed = _embed(
                (f"Très probable copie de Wikipédia sur {self.site.lang}:{page_name}" if self.site.lang_bot == "fr" else f"Most likely copy from Wikipedia on {self.site.lang}:{page_name}"),
                ("Cette page copie très probablement Wikipédia." if self.site.lang_bot == "fr" else "This page most likely copies Wikipedia."),
                13371938,
            )
            _send_webhook(webhooks_url.get(self.site.family), {"embeds": [embed]})

        elif prob_WP >= 75:
            embed = _embed(
                (f"Probable copie de Wikipédia sur {self.site.lang}:{page_name}" if self.site.lang_bot == "fr" else f"Likely copy from Wikipedia on {self.site.lang}:{page_name}"),
                ("Cette page copie probablement Wikipédia." if self.site.lang_bot == "fr" else "This page likely copies Wikipedia."),
                12138760,
            )
            _send_webhook(webhooks_url.get(self.site.family), {"embeds": [embed]})

        elif prob_WP >= 50:
            embed = _embed(
                (f"Possible copie de Wikipédia sur {self.site.lang}:{page_name}" if self.site.lang_bot == "fr" else f"Possible copy from Wikipedia on {self.site.lang}:{page_name}"),
                ("Cette page copie possiblement Wikipédia." if self.site.lang_bot == "fr" else "This page likely copies Wikipedia."),
                12138760,
            )
            _send_webhook(webhooks_url.get(self.site.family), {"embeds": [embed]})

    def _daily_stats_and_webhook(self, detailed_diff_info: Dict[int, Dict[str, Any]], since: datetime.datetime) -> None:
        pywikibot.output("Sauvegarde des modifications récentes du jour.")
        with open(f"rc_{self.site.family}_{self.site.lang}_{since.strftime('%Y%m%d')}.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(detailed_diff_info))

        scores_n: Dict[int, int] = {}
        scores_n_reverted: Dict[int, int] = {}
        ip_edits = user_edits = ip_edits_rev = user_edits_rev = 0
        ips: set[str] = set()
        users: set[str] = set()
        ips_rev: set[str] = set()
        users_rev: set[str] = set()

        for info in detailed_diff_info.values():
            if "score" not in info or info.get("trusted"):
                continue

            score = info["score"]
            scores_n[score] = scores_n.get(score, 0) + 1
            scores_n_reverted.setdefault(score, 0)

            is_anon = info.get("anon", False)
            user = info.get("user", "")

            if is_anon:
                ip_edits += 1
                ips.add(user)
            else:
                user_edits += 1
                users.add(user)

            if info.get("reverted"):
                scores_n_reverted[score] += 1
                if is_anon:
                    ip_edits_rev += 1
                    ips_rev.add(user)
                else:
                    user_edits_rev += 1
                    users_rev.add(user)

        n_contribs = user_edits + ip_edits
        n_contribs_rev = user_edits_rev + ip_edits_rev

        def _ratio(n: int, d: int) -> float:
            return (n / d) if d else 0.0

        prop_ip_contribs = _ratio(ip_edits_rev, ip_edits)
        prop_user_contribs = _ratio(user_edits_rev, user_edits)
        prop_contribs = _ratio(n_contribs_rev, n_contribs)

        n_users_reverted = len(users_rev)
        n_ip_reverted = len(ips_rev)
        n_users = len(users)
        n_ip = len(ips)

        prop_ip = _ratio(n_ip_reverted, n_ip)
        prop_user = _ratio(n_users_reverted, n_users)
        prop_users_ip = _ratio(n_users_reverted + n_ip_reverted, n_users + n_ip)

        # file with reverted proportions per negative score (original behavior)
        scores_x, scores_y, scores_rev, scores_tot = [], [], [], []
        for s, tot in scores_n.items():
            if s < 0:
                scores_x.append(abs(s))
                scores_y.append(scores_n_reverted.get(s, 0) / tot if tot else 0)
                scores_rev.append(scores_n_reverted.get(s, 0))
                scores_tot.append(tot)

        with open(f"vand_{self.site.family}_{self.site.lang}_{since.strftime('%Y%m%d')}.txt", "w", encoding="utf-8") as f:
            for x, r, t in zip(scores_x, scores_rev, scores_tot):
                f.write(f"{x}:{r}/{t}\r\n")

        if prop_users_ip <= 0 or not webhooks_url.get(self.site.family):
            return

        if self.site.lang_bot == "fr":
            fields = [
                {"name": "IP et nouveaux révoqués/Nombre total d'IP et nouveaux (non-Autoconfirmed) actifs", "value": f"{n_ip_reverted+n_users_reverted}/{n_users+n_ip} ({round(prop_users_ip*100, 2)} %)", "inline": False},
                {"name": "IP révoquées/Nombre total d'IPs", "value": f"{n_ip_reverted}/{n_ip} ({round(prop_ip*100, 2)} %)", "inline": True},
                {"name": "Nouveaux inscrits révoqués/Nouveaux inscrits (non-Autoconfirmed) actifs", "value": f"{n_users_reverted}/{n_users} ({round(prop_user*100, 2)} %)", "inline": True},
                {"name": "Modifications révoquées/Modifications totales des nouveaux (IP + utilisateurs non-Autoconfirmed)", "value": f"{n_contribs_rev}/{n_contribs} ({round(prop_contribs*100, 2)} %)", "inline": False},
                {"name": "Modifications révoquées/Modifications IP", "value": f"{ip_edits_rev}/{ip_edits} ({round(prop_ip_contribs*100, 2)} %)", "inline": True},
                {"name": "Modifications révoquées/Modifications nouveaux utilisateurs inscrits (non-Autoconfirmed)", "value": f"{user_edits_rev}/{user_edits} ({round(prop_user_contribs*100, 2)} %)", "inline": True},
            ]
            title = f"Statistiques sur {self.site.family} {self.site.lang} (dernières 24 h)"
            desc = "Statistiques sur la patrouille (humains et bot):"
        else:
            fields = [
                {"name": "Reverted users/Total new users (no Autoconfirmed) and IP number", "value": f"{n_ip_reverted+n_users_reverted}/{n_users+n_ip} ({round(prop_users_ip*100, 2)} %)", "inline": False},
                {"name": "Reverted IP/Total IP number", "value": f"{n_ip_reverted}/{n_ip} ({round(prop_ip*100, 2)} %)", "inline": True},
                {"name": "Reverted users/Total users number", "value": f"{n_users_reverted}/{n_users} ({round(prop_user*100, 2)} %)", "inline": True},
                {"name": "Reverted edits/Total new users (no Autoconfirmed) and IP edits", "value": f"{n_contribs_rev}/{n_contribs} ({round(prop_contribs*100, 2)} %)", "inline": False},
                {"name": "Reverted edits/IP edits", "value": f"{ip_edits_rev}/{ip_edits} ({round(prop_ip_contribs*100, 2)} %)", "inline": True},
                {"name": "Reverted edits/New users (no Autoconfirmed) edits", "value": f"{user_edits_rev}/{user_edits} ({round(prop_user_contribs*100, 2)} %)", "inline": True},
            ]
            title = f"Statistics about {self.site.family} {self.site.lang} (last 24 h)"
            desc = "Statistics about patrolling (humans and bot):"

        _send_webhook(webhooks_url[self.site.family], {"embeds": [{"title": title, "description": desc, "color": 65535, "fields": fields}]})

    # ----------------------------
    # Main loop
    # ----------------------------

    def execute(self) -> None:
        self.datetime_utcnow = datetime.datetime.utcnow()
        month = int(self.datetime_utcnow.strftime("%m"))
        day = int(self.datetime_utcnow.strftime("%d"))

        while True:
            self.datetime_utcnow = datetime.datetime.utcnow()
            try:
                if self.site.bot_stopped():
                    self.send_message_bot_stopped()
                    print("Le bot a été arrêté.")
                    break
                if not self.ignore_task_month and (self.start_task_month or int(self.datetime_utcnow.strftime("%m")) != month):
                    self.task_every_month()
                    self.start_task_month = False
                    month = int(self.datetime_utcnow.strftime("%m"))

                if self.start_task_day or int(self.datetime_utcnow.strftime("%d")) != day:
                    self.task_every_day()
                    self.start_task_day = False
                    day = int(self.datetime_utcnow.strftime("%d"))

                self.task_every_10minutes()

            except Exception:
                _safe_log_exc()

            time.sleep(600)  # Pause de 10 minutes