# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals

from pywikibot import family


class Family(family.SubdomainFamily):

    """Family class for Dicoado."""

    name = 'dicoado'
    domain = 'dicoado.org'
    langs = {
        'fr': 'dicoado.org',
    }

    def protocol(self, code):
        """Return https as the protocol for this family."""
        return 'https'

    def scriptpath(self, code):
        return '/wiki'
