repopath=$1
mgmtdir="/home/git/repo-management/"

cd $repopath
for line in $( find -name "*.git" -not -path "./qt/*" -not -path "./clones/*" -not -path "./scratch/*" ); do
    cd $repopath/$line/

    currpath=$(pwd)
    urlpath=${currpath#/srv/git/repositories/}
    reponame=${urlpath%.git}

    # Gitolite-admin is private, skip it
    if [[ "$urlpath" == "gitolite-admin.git" ]]; then
        continue
    fi

    # Build the remote URL up
    remoteurl="staging@code.kde.org:$reponame"
    # Now we push it up there
    python $mgmtdir/helpers/update-repo-mirror.py "$reponame" "$remoteurl"
done
