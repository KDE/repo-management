repopath=$1
mgmtdir="/home/git/repo-management/"

cd $repopath
for line in $( find -mindepth 1 -maxdepth 1 -type d -name "*.git" ); do
    cd $repopath/$line/

    currpath=$(pwd)
    urlpath=${currpath#/srv/git/repositories/}
    reponame=${urlpath%.git}

    # Gitolite-admin is private, skip it
    if [[ "$urlpath" == "gitolite-admin.git" ]]; then
        continue
    fi

    # Build the remote URL up
    remoteurl="git@github.com:kde/$reponame"
    # Make sure the repo exists on Github
    python $mgmtdir/bin/create-on-github.py "$reponame" "/srv/git/repositories/$urlpath"
    # Now we push it up there
    python $mgmtdir/bin/update-repo-mirror.py "$reponame" "$remoteurl"

    # To avoid DoSing them, we now wait 30 seconds
    sleep 30s
done
