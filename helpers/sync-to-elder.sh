# Static Config
mgmtdir="/home/git/repo-management"

# Grab our input
reponame="$1"

# Build the remote URL up
remoteurl="git@elder.kde.org:$reponame"
# Now we push it up there
cd "/srv/git/repositories/$reponame"
git push --mirror "$remoteurl"
