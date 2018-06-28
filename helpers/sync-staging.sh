# Static Config
mgmtdir="/home/git/repo-management"

# Grab our input
reponame="$1"

# Build the remote URL up
remoteurl="staging@code.kde.org:$reponame"
# Now we push it up there
cd "/srv/git/repositories/$reponame"
python $mgmtdir/helpers/update-repo-mirror.py "$reponame" "$remoteurl"
