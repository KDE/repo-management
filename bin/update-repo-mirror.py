#!/usr/bin/python
# Repository mirror updater. Invokes git in a custom manner and transfers across only branch and tag changes. For use with services such as Github/Gitorious

import re
import sys
import subprocess

# Read arguments...
try:
    repository_name = sys.argv[1]
    update_target = sys.argv[2]
except IndexError:
    usage()

# Find out what has supposedly changed....
# Note: it must be run under a shell as git is silly
command = "git push --mirror -n --porcelain '{0}'".format( update_target )
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
refs_changed = process.stdout.readlines()

changes = []
for ref in refs_changed:
    # Look to see if it is done to a branch or tag....
    # Everything else is not relevant - and should be ignored....
    match = re.match('^[-|*| ]\t(.*refs/(heads|tags)/\S+)\t(.+)\n', ref)
    if match:
        changes.append( match.group(1) )
        continue

# Check if we actually need to do anything
if changes == []:
    exit

# Commence the mirror updating!
updating_refs = ' '.join(changes)
command = "git push -f '{0}' {1}".format( update_target, updating_refs )
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)