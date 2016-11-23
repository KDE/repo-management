#!/bin/bash

repopath=$1

cd $repopath
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do cd $repopath/$line/; git gc; git prune; done

cd /repositories/sysadmin
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do cd $repopath/sysadmin/$line/; git gc; git prune; done

cd /repositories/websites
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do cd $repopath/websites/$line/; git gc; git prune; done

cd /repositories/scratch
for line in $( find -mindepth 2 -maxdepth 2 -type d -name "*.git" ); do cd $repopath/scratch/$line/; git gc; git prune; done

cd /repositories/clones
for line in $( find -mindepth 3 -maxdepth 3 -type d -name "*.git" ); do cd $repopath/clones/$line/; git gc; git prune; done