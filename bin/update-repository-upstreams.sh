mgmtdir="/home/git/repo-management"
repobase="/srv/git/repositories"

for upstreamrepo in `ls $mgmtdir/repo-configs/upstream/`; do
    remoteurl=`cat $mgmtdir/repo-configs/upstream/$upstreamrepo`
    repo=$repobase/$upstreamrepo
    cd $repo
    git fetch -n "$remoteurl" +refs/heads/*:refs/upstream/heads/* +refs/tags/*:refs/upstream/tags/*
    $mgmtdir/hooks/post-update
done

cd $mgmtdir/repo-configs/mirror/
for mirrorrepo in `find -type f`; do
    remoteurl=`cat $mgmtdir/repo-configs/mirror/$mirrorrepo`
    repo=$repobase/$mirrorrepo
    cd $repo
    python $mgmtdir/bin/repository-mirror-updater.py "$remoteurl"
    $mgmtdir/hooks/post-update
done
