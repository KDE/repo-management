#!/usr/bin/python
# Repository mirror updater. Invokes git in a custom manner and transfers across only branch and tag changes. For use with services such as Github/Gitorious

import re
import sys
import subprocess

# Read arguments...
try:
    localRepository = sys.argv[1]
except IndexError:
    usage()

# Make sure we have a mainline repository
# If this isn't a mainline/website/sysadmin repository - bail
if not localRepository.startswith("kde/") or localRepository.startswith("websites/") or localRepository.startswith("sysadmin/"):
    sys.exit(0)

# If this is a mainline repository we need to fix the path to match git.kde.org
if localRepository.startswith("kde/"):
    localRepository = localRepository[4:]

# Determine the URL of the repository on git.kde.org
remoteRepository = "git@git.kde.org:{}".format( localRepository )

# Find out what has supposedly changed....
# Note: it must be run under a shell as git is silly
command = "git push --mirror -n --porcelain '{0}'".format( remoteRepository )
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
refs_changed = process.stdout.readlines()

changes = []
for ref in refs_changed:
    # Look to see if it is done to a branch or tag....
    # Everything else is not relevant - and should be ignored....
    match = re.match('^[-|*| |+]\t(.*refs/(heads|tags)/\S+)\t(.+)\n', ref)
    if not match:
        continue

    # Now that we only have branches and tags - make sure this isn't a Phabricator staging tag
    # These need to be ignored as they can't be replicated to git.kde.org
    match = re.match('^[-|*| |+]\t(.*refs/tags/phabricator/\S+)\t(.+)\n', ref)
    if match:
        continue

    # Now that we've ensured all of those are cleared, add it to our list!
    match = re.match('^[-|*| |+]\t(.*refs/(heads|tags)/\S+)\t(.+)\n', ref)
    changes.append( match.group(1) )

# Check if we actually need to do anything
if changes == []:
    sys.exit(0)

# Commence the mirror updating!
updating_refs = ' '.join(changes)
command = "git push '{0}' {1}".format( remoteRepository, updating_refs )
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
