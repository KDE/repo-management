#!/bin/sh

cd /home/git/repo-uid-mappings
for repouid in $( find /home/git/metadata-tree -name "kde-repo-uid" ); do
    uid=$(cat $repouid)
    dir=$(dirname $repouid)
    dir=${dir#/home/git/metadata-tree/}
    echo $dir > $uid
done
