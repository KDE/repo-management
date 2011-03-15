for upstreamrepo in `find /srv/kdegit/repositories -name kde-upstream`; do
    remoteurl=`cat $upstreamrepo`
    repo=`dirname $upstreamrepo`
    cd $repo
    git fetch -n "$remoteurl" +refs/heads/*:refs/upstream/heads/* +refs/tags/*:refs/upstream/tags/*
done
