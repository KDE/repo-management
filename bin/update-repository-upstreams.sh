mgmtdir="/home/git/repo-management"
repobase="/srv/kdegit/repositories"

for upstreamrepo in `ls $mgmtdir/repo-configs/upstream/`; do
    remoteurl=`cat $mgmtdir/repo-configs/upstream/$upstreamrepo`
    repo=$repobase/$upstreamrepo
    cd $repo
    git fetch -n "$remoteurl" +refs/heads/*:refs/upstream/heads/* +refs/tags/*:refs/upstream/tags/*
done

for mirrorrepo in `ls $mgmtdir/repo-configs/mirror/`; do
    remoteurl=`cat $mgmtdir/repo-configs/mirror/$mirrorrepo`
    repo=$repobase/$mirrorrepo
    cd $repo
    git fetch -n "$remoteurl" +refs/heads/*:refs/heads/* +refs/tags/*:refs/tags/*
done
