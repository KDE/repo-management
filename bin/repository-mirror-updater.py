#!/usr/bin/python
# Local repository mirror updater which ensures HEAD is updated to follow remote changes - something Git will never do for us
import re
import sys
import subprocess

# Read arguments...
try:
    remoteUrl = sys.argv[1]
except IndexError:
    exit()

# Perform the general repository update
command = "git fetch -n '{0}' +refs/heads/*:refs/heads/* +refs/tags/*:refs/tags/*".format( remoteUrl )
subprocess.call(command, shell=True, stdout=subprocess.STDOUT, stderr=subprocess.STDERR)

# Now we perform the HEAD update, first thing is to get some remote repository metadata
command = "git remote show '{0}'".format( remoteUrl )
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
remoteMetadata = process.stdout.readlines()

# Now we search in the metadata for the key piece of information
for metadata in remoteMetadata:
    # We are looking for a single line
    match = re.match("^  HEAD branch: (.*)$", metadata)
    if match:
        # Update HEAD and stop processing
        remoteHeadBranch = match.group(1)
        command = "git symbolic-ref -q HEAD 'refs/heads/{0}'".format( remoteHeadBranch )
        subprocess.call(command, shell=True, stdout=subprocess.STDOUT, stderr=subprocess.STDOUT)
        break
