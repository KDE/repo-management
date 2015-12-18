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

import subprocess

class AnongitRemote(object):

    def __init__(self, name, host, desc = "This repository has no description"):

        self.HOST = host
        self.REPO_NAME = name
        self.REPO_DESC = desc

    def __repr__(self):

        return ("<AnongitRemote for %s:%s>" % (self.HOST, self.REPO_NAME))

    def __runSshCommand(self, command):

        cmdContext = ("ssh", self.HOST, command)
        ssh = subprocess.Popen(cmdContext, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = False)
        result = ssh.stdout.readlines()

        if "OK" in result:
            return True
        result = ssh.stderr.readlines()
        return False

    def setRepoDescription(self, desc):

        self.REPO_DESC = desc
        if self.repoExists():
            command = ("SETDESC %s \"%s\"" % self.REPO_NAME, self.REPO_DESC)
            return self.__runSshCommand(command)
        return True

    def repoExists(self):

        command = ("EXISTS %s" % self.REPO_NAME)
        return self.__runSshCommand(command)

    def createRepo(self):

        command = ("CREATE %s \"%s\"" % self.REPO_NAME, self.REPO_DESC)
        return self.__runSshCommand(command)

    def deleteRepo(self):

        command = ("DELETE %s" % self.REPO_NAME)
        return self.__runSshCommand(command)

    def moveRepo(self, newname):

        command = ("CREATE %s" % self.REPO_NAME)
        ret = self.__runSshCommand(command)

        if ret:
            self.REPO_NAME = newname
            return True
        return False
