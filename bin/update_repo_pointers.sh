#!/bin/sh

cd /home/git/repo-uid-mappings

# These copy the names in the each-repo-has-it kde-repo-uid file and 
# each-repo-may-have-it kde-repo-nick file into files in /home/git/metadata-tree
# so that the commits URL resolver can use it to look up the actual URL
for repouid in $( find /home/git/metadata-tree -name "kde-repo-uid" ); do
    uid=$(cat $repouid)
    dir=$(dirname $repouid)
    dir=${dir#/home/git/metadata-tree/}
    echo $dir > $uid
done
for reponick in $( find /home/git/metadata-tree -name "kde-repo-nick" ); do
    nick=$(cat $reponick)
    dir=$(dirname $reponick)
    dir=${dir#/home/git/metadata-tree/}
    echo $dir > $nick
done

