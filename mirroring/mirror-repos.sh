#!/bin/bash
# Bail if we have an error
set -e

# Our parameters
baseDirectory=$1
reposToMirror=$2

# Read the token we will use for pushing changes
gitlabToken=$(cat ~/.gitlab-token)

# Ensure that the base directory exists
if [ ! -d $baseDirectory ]; then
    mkdir -p $baseDirectory
fi

# Retrieve the list of repositories we are going to mirror and perform the necessary action
cat $reposToMirror | while read repositoryEntry; do
    # Reset our working directory to begin with
    cd $baseDirectory

    # Now breakout the Gitlab path and the upstream url
    gitlabPath=`echo $repositoryEntry | cut -d " " -f 1`
    upstreamUrl=`echo $repositoryEntry | cut -d " " -f 2`

    # Construct the local path (which will match the Gitlab Path)
    localMirrorPath="$baseDirectory/$gitlabPath.git"

    # Ensure the folder containing the local copy exists for Git to make use of
    localMirrorBase=`dirname $localMirrorPath`
    if [ ! -e $localMirrorBase ]; then
        mkdir -p $localMirrorBase
    fi

    # Do we need to setup the initial clone of the repository?
    if [ ! -e $localMirrorPath ]; then
        git clone --mirror $upstreamUrl $localMirrorPath
    fi

    # Update the local mirror
    cd $localMirrorPath
    git remote update -p

    # Publish it to invent.kde.org
    python2 ~/repo-management/helpers/update-repo-mirror.py $gitlabPath https://oauth:$gitlabToken@invent.kde.org/$gitlabPath
done
