# This file is part of Propagator, a KDE Sysadmin Project
#
# Copyright 2015 Boudhayan Gupta <bgupta@kde.org>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of KDE e.V. (or its successor approved by the
#    membership of KDE e.V.) nor the names of its contributors may be used
#    to endorse or promote products derived from this software without
#    specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import requests
import ConfigParser

try:
    import simplejson as json
except ImportError:
    import json

class GithubRemote(object):

    def __init__(self, name, desc = "This repository has no description"):

        config = ConfigParser.ConfigParser()
        config.read(os.path.expanduser('~/.github-mirrorrc'))

        self.REPO_NAME = name
        self.REPO_DESC = desc
        self.ACCESS_TOKEN = config.get('Github', 'access_token')
        self.ORGANISATION = config.get('Github', 'organisation')

        self.SESSION = requests.Session()
        self.SESSION.headers.update({"Accept": "application/vnd.github.v3+json"})
        self.SESSION.headers.update({"Authorization": " ".join(("token", ACCESS_TOKEN))})

    def __repr__(self):

        return ("<GithubRemote for kde:%s.git>" % self.REPO_NAME)

    def setRepoDescription(self, desc):

        self.REPO_DESC = desc

    def repoExisis(self):

        url = "/".join(("https://api.github.com/repos", self.ORGANISATION, self.REPO_NAME))
        r = self.SESSION.get(url)

        if (r.ok) and ("id" in r.json.keys()):
            return True
        return False

    def createRepo(self):

        payload = {
            "name": self.REPO_NAME,
            "description": self.REPO_DESC,
            "private": False,
            "has_issues": False,
            "has_wiki": False,
            "has_downloads": False,
            "auto_init": False,
        }

        url = "/".join(("https://api.github.com/orgs", self.ORGANISATION, "repos"))
        r = self.SESSION.post(url, data = json.dumps(payload))

        if (r.status_code == 201) and ("id" in r.json.keys()):
            return True
        return False

    def deleteRepo(self):

        url = "/".join(("https://api.github.com/repos", self.ORGANISATION, self.REPO_NAME))
        r = self.SESSION.delete(url)

        if (r.status_code == 204):
            return True
        return False

    def moveRepo(self, newname):

        payload = {"name": newname}
        url = "/".join(("https://api.github.com/repos", self.ORGANISATION, self.REPO_NAME))
        r = self.SESSION.patch(url, data = json.dumps(payload))

        if (r.status_code == 201) and ("id" in r.json.keys()):
            self.REPO_NAME = newname
            return True
        return False
