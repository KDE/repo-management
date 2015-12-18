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

from SyncJob import doSync

# some path constants without which we won't be able to get
# to the configuration

MGMTDIR = "/home/git/repo-management"
CFGFILE = os.path.join(MGMTDIR, config, "PropagatorConfig.json")

# initialise the celery worker

app = celery.Celery()
app.conf.CELERY_TASK_SERIALIZER = "pickle"
app.conf.CELERY_ACCEPT_CONTENT = ["pickle"]
app.conf.CELERYD_CONCURRENCY = 2

# all exported tasks

@app.task(ignore_result = True)
def CreateRepo(repo):
    print("Creating Repo")

@app.task(ignore_result = True)
def RenameRepo(srcRepo, destRepo):
    print("Renaming Repo")

@app.task(ignore_result = True)
def UpdateRepo(repo):

    # start by bringing up a list of all anongit servers


@app.task(ignore_result = True)
def DeleteRepo(repo):
    print("Deleting Repo")

# non-exported tasks - individual sync jobs, etc

@app.task(ignore_result = True)
def p_SyncRepo(repo, remote, restricted):

    ret = doSync(repo, remote, restricted)
    if ret:
        return

    backoff = 60 * (self.request.retries + 1)
    if backoff > 1800: # 30 minutes
        return
    raise self.retry(countdown = backoff, max_retries = None)
