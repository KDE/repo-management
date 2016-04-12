# Static Config
mgmtdir="/home/git/repo-management"

# Grab our input
reponame="$1"
urlpath="$2"

# Build the remote URL up
remoteurl="git@github.com:kde/$reponame"
# Make sure the repo exists on Github
python $mgmtdir/bin/create-on-github.py "$reponame" "/srv/git/repositories/$urlpath"
# Now we push it up there
python $mgmtdir/bin/update-repo-mirror.py "$reponame" "$remoteurl"