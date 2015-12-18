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

import celery
import os
import re

try:
    import simplejson as json
except ImportError:
    import json

from SyncJob import doSync
from GithubRemote import GithubRemote
from AnongitRemote import AnongitRemote

# some path constants without which we won't be able to get
# to the configuration

MGMTDIR = "/home/git/repo-management"
CFGFILE = os.path.join(MGMTDIR, config, "PropagatorConfig.json")
CFGDATA = {}

with open(CFGFILE) as f:
    CFGDATA = json.load(f)

# utility functions

def isExcept(repo, config):

    for pattern in config:
        p = re.compile(pattern)
        if p.match(repo):
            return True
    return False

# initialise the celery worker

app = celery.Celery()
app.conf.CELERY_TASK_SERIALIZER = "pickle"
app.conf.CELERY_ACCEPT_CONTENT = ["pickle"]
app.conf.CELERYD_CONCURRENCY = 2

# all exported tasks

@app.task(ignore_result = True)
def CreateRepo(repo):

    # find our repository and read in the description
    repoRoot = CFGDATA["RepoRoot"]
    repoPath = os.path.join(repoRoot, repo)
    if not os.path.exists(repoPath):
        return

    repoDesc = "This repository has no description"
    repoDescFile = os.path.join(repoPath, "description")
    if os.path.exists(repoDescFile):
        with open(repoDescFile) as f:
            repoDesc = f.read().strip()

    # spawn the create tasks
    if not isExcept(repo, CFGDATA["GithubExcepts"]):
        p_CreateRepoGithub.delay(repo, repoDesc)

    if not isExcept(repo, CFGDATA["AnongitExcepts"]):
        for server in CFGDATA["AnongitServers"]:
            p_CreateRepoAnongit.delay(repo, server, repoDesc)

@app.task(ignore_result = True)
def RenameRepo(srcRepo, destRepo):

    if not isExcept(repo, CFGDATA["GithubExcepts"]):
        p_MoveRepoGithub.delay(srcRepo, destRepo)

    if not isExcept(repo, CFGDATA["AnongitExcepts"]):
        for server in CFGDATA["AnongitServers"]:
            p_CreateRepoAnongit.delay(srcRepo, destRepo, server)

@app.task(ignore_result = True)
def UpdateRepo(repo):

    # find our repository
    repoRoot = CFGDATA["RepoRoot"]
    repoPath = os.path.join(repoRoot, repo)
    if not os.path.exists(repoPath):
        return

    # spawn push to github task first
    if not isExcept(repo, CFGDATA["GithubExcepts"]):
        githubPrefix = CFGDATA["GithubPrefix"]
        githubUser = CFGDATA["GithubUser"]
        githubRemote = "%s@github.com:%s/%s" % (githubUser, githubPrefix, repo)
        p_SyncRepo.delay(repoPath, githubRemote, True)

    # now spawn all push to anongit tasks
    if not isExcept(repo, CFGDATA["AnongitExcepts"]):
        anonUser = CFGDATA["AnongitUser"]
        anonPrefix = CFGDATA["AnongitPrefix"]
        for server in CFGDATA["AnongitServers"]:
            anonRemote = "%s@%s:%s/%s" % (anonUser, server, anonPrefix, repo)
            p_SyncRepo.delay(repoPath, anonRemote, False)

@app.task(ignore_result = True)
def DeleteRepo(repo):

    if not isExcept(repo, CFGDATA["GithubExcepts"]):
        p_DeleteRepoGithub.delay(repo)

    if not isExcept(repo, CFGDATA["AnongitExcepts"]):
        for server in CFGDATA["AnongitServers"]:
            p_DeleteRepoAnongit.delay(repo, server)

# non-exported tasks - individual sync jobs, etc

@app.task(ignore_result = True)
def p_DeleteRepoGithub(repo):

    if repo.endswith(".git"):
        repo = repo[:-4]
    remote = GithubRemote(repo)

    if remote.repoExists():
        remote.deleteRepo()

@app.task(ignore_result = True)
def p_DeleteRepoAnongit(repo, server):

    remote = AnongitRemote(name, server)
    if remote.repoExists():
        remote.deleteRepo()

@app.task(ignore_result = True)
def p_SyncRepo(repo, remote, restricted):

    ret = doSync(repo, remote, restricted)
    if ret:
        return

    backoff = 60 * (self.request.retries + 1)
    if backoff > 1800: # 30 minutes
        return # log it somewhere first?
    raise self.retry(countdown = backoff, max_retries = None)

@app.task(ignore_result = True)
def p_CreateRepoGithub(repo, desc):

    if repo.endswith(".git"):
        repo = repo[:-4]
    remote = GithubRemote(repo, desc)

    if not remote.repoExists():
        remote.createRepo()

@app.task(ignore_result = True)
def p_CreateRepoAnongit(repo, server, desc):

    remote = AnongitRemote(repo, server, desc)
    if not remote.repoExists():
        remote.createRepo()

@app.task(ignore_result = True)
def p_MoveRepoGithub(src, dest):

    if src.endswith(".git"):
        src = src[:-4]
    if dest.endswith(".git"):
        dest = dest[:-4]
    remote = GithubRemote(src)

    if remote.repoExists():
        remote.moveRepo(dest)

@app.task(ignore_result = True)
def p_MoveRepoAnongit(src, dest, server):

    remote = AnongitRemote(src, server)
    if remote.repoExists():
        remote.moveRepo(dest)
