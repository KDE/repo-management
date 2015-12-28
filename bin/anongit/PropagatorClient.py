#!/usr/bin/python3
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
import shlex
import git

REPO_ROOT = os.path.expanduser("~/kde")

def setRepoDescription(repoName, repoDesc):

    repoDir = os.path.join(REPO_ROOT, repoName)
    if not os.path.exists(repoDir):
        print("ERROR: Repo does not exist")
        return False

    with open(os.path.join(repoDir, "description"), "w") as f:
        f.write(repoDesc.strip() + "\n")
    return True

def createRepo(repoName, repoDesc):

    repoDir = os.path.join(REPO_ROOT, repoName)
    if os.path.exists(repoDir):
        print("ERROR: Repo already exists")
        return False

    repo = git.Repo.init(repoDir)
    if repo.bare:
        return setRepoDescription(repoName, repoDesc)
    print("ERROR: Failed to create repo")
    return False

def repoExists(repoName):

    repoDir = os.path.join(REPO_ROOT, repoName)
    if os.path.exists(repoDir):
        try:
            repo = git.Repo(repoDir)
        except git.exc.InvalidGitRepositoryError:
            print("ERROR: Repo does not exist")
            return False
        return True

    print("ERROR: Repo does not exist")
    return False

def renameRepo(oldRepo, newRepo):

    oldRepoPath = os.path.abspath(os.path.join(REPO_ROOT, oldRepo))
    newRepoPath = os.path.abspath(os.path.join(REPO_ROOT, newRepo))

    if not os.path.exists(oldRepoPath):
        print("ERROR: Source repo does not exist")
        return False

    if os.path.exists(newRepoPath):
        print("ERROR: Destination repo already exists")
        return False

    basePath = os.path.dirname(newRepoPath)
    if not os.path.exists(basePath):
        os.makedirs(basePath)
    shutil.move(oldRepoPath, newRepoPath)
    return True

def deleteRepo(repoName):

    repoDir = os.path.join(REPO_ROOT, repoName)
    if not os.path.exists(repoDir):
        print("ERROR: Repo does not exist")
        return False

    shutil.rmtree(path)
    return True

def processCommand(commandList):

    cmd = commandList[0]
    repoName = commandList[1]

    if cmd == "EXISTS":
        return repoExists(repoName)
    elif cmd == "SETDESC":
        repoDesc = commandList[2]
        return setRepoDescription(repoName, repoDesc)
    elif cmd == "CREATE":
        repoDesc = commandList[2]
        return createRepo(repoName, repoDesc)
    elif cmd == "DELETE":
        return deleteRepo(repoName)
    elif cmd == "MOVE":
        newRepo = commandList[2]
        return moveRepo(repoName, newRepo)
    else:
        print("ERROR: Invalid command entered. This account does not allow shell access.")
        return False

if __name__ == "__main__":

    soc = os.environ.get("SSH_ORIGINAL_COMMAND")
    if not soc:
        print("ERROR: Invalid command entered. This account does not allow shell access.")
        print("FAIL")
        sys.exit(1)

    socList = shlex.split(soc)
    ret = processCommand(socList)
    if ret:
        print("OK")
        sys.exit(0)
    print("FAIL")
    sys.exit(1)
