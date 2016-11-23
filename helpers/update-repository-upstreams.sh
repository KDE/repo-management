mgmtdir="/home/git/repo-management"
repobase="/srv/git/repositories"

cd $mgmtdir/repo-configs/mirror/
for mirrorrepo in `find -type f`; do
    remoteurl=`cat $mgmtdir/repo-configs/mirror/$mirrorrepo`
    repo=$repobase/$mirrorrepo
    cd $repo
    python $mgmtdir/helpers/repository-mirror-updater.py "$remoteurl"
    $mgmtdir/hooks/post-update
done
