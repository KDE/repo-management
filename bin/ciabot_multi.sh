#!/usr/bin/env bash
# Distributed under the terms of the GNU General Public License v2
# Copyright (c) 2006 Fernando J. Pereda <ferdy@gentoo.org>
#
# Git CIA bot in bash. (no, not the POSIX shell, bash).
# It is *heavily* based on Git ciabot.pl by Petr Baudis.
#
# It is meant to be run either on a post-commit hook or in an update
# hook:
#
# post-commit: It parses latest commit and current HEAD to get the
# information it needs.
#
# update: You have to call it once per merged commit:
#
#       refname=$1
#       oldhead=$2
#       newhead=$3
#       for merged in $(git rev-list ${oldhead}..${newhead} | tac) ; do
#               /path/to/ciabot.bash ${refname} ${merged} [module name] [url prefix]
#       done
#

# Project identifier (git repo name sans trailing .git)
module="$3"

# Set to true if you want the full log to be sent
noisy=true

# Addresses for the e-mail
from="sysadmin@kde.org"
to="cia@cia.vc"

# SMTP client to use
sendmail="/usr/sbin/sendmail ${to}"

# Changeset URL
url="$4@@sha1@@"

# You shouldn't be touching anything else.
if [[ $# = 0 ]] ; then
	refname=$(git symbolic-ref HEAD 2>/dev/null)
	merged=$(git rev-parse HEAD)
else
	refname=$1
	merged=$2
fi

refname=${refname##refs/heads/}

gitver=$(git --version)
gitver=${gitver##* }

rev=$(git describe --tags ${merged} 2>/dev/null)
[[ -z ${rev} ]] && rev=${merged:0:12}

rawcommit=$(git cat-file commit ${merged})

logmessage=$(sed -e '1,/^$/d' <<< "${rawcommit}")
${noisy} || logmessage=$(head -n 1 <<< "${logmessage}")
logmessage=${logmessage//&/&amp;}
logmessage=${logmessage//</&lt;}
logmessage=${logmessage//>/&gt;}

author=$(git log --encoding=UTF-8 -n1 --pretty=format:%an ${merged})

silent=$(echo "$logmessage" | egrep -q "(CVS|SVN|GIT)_SILENT")$?

# Don't push silent commits made by scripty to CIA
if [ "$author" = "Script Kiddy" -a "$silent" -eq 0 ]; then
    exit 0
fi

ts=$(sed -n -e '/^author .*> \([0-9]\+\).*$/s--\1-p' \
	<<< "${rawcommit}")

out="
<message>
  <generator>
    <name>CIA Bash client for Git</name>
    <version>${gitver}</version>
    <url>http://dev.gentoo.org/~ferdy/stuff/ciabot.bash</url>
  </generator>
  <source>
    <project>KDE</project>
    <module>${module}</module>
    <branch>${refname}</branch>
  </source>
  <timestamp>${ts}</timestamp>
  <body>
    <commit>
      <author>${author}</author>
      <revision>${rev}</revision>
      <files>
        $(git diff-tree -r --name-only ${merged} |
          sed -e '1d' -e 's-.*-<file>&</file>-')
      </files>
      <log>
${logmessage}
      </log>
      <url>${url//@@sha1@@/${merged}}</url>
    </commit>
  </body>
</message>"

${sendmail} << EOM
Message-ID: <${merged:0:12}.${author}@${module}>
From: ${from}
To: ${to}
Subject: DeliverXML
MIME-Version: 1.0
Content-Type: text/xml; charset=UTF-8
Content-Transfer-Encoding: 8bit
${out}
EOM

# vim: set tw=70 :

