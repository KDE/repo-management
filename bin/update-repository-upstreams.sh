for upstreamrepo in `find /srv/kdegit/repositories -name kde-upstream`; do
    remoteurl=`cat $upsteamrepo`
    repo=`dirname $upstreamrepo`
    cd $repo
    git fetch "$remoteurl" +refs/heads/*:refs/upstream/heads/* +refs/tags/*:refs/upstream/tags/*
done
