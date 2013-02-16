cd /srv/kdegit/repositories/
DATA=''
for repo in $(find -maxdepth 2 -name "*.git" -type d); do
    export GIT_DIR=$repo/

    list=$(git branch)
    list2=$(git tag)
    if [ "$list" == "" -a "$list2" == "" ]; then
        repofilled=0
    else
        repofilled=1
    fi

    if [ ! -f $repo/gl-creater -a -f $repo/kde-hooks-off ]; then
        # Hooks are off in these tests....
        if [ $repofilled != 0 ]; then
            # Forgot to switch off after filling...
            DATA="$repo is USED with hooks DISABLED (POLICY VIOLATION)\n$DATA"
        fi
    else
        # Hooks are on in these tests....
        if [ ! -f $repo/gl-creater -a $repofilled == 0 ]; then
            # May cause a flood!!!
            DATA="$repo is NOT USED with hooks ENABLED (FLODD WARNING)\n$DATA"
        fi
        # The other case here is normal, so we don't look for that
        # We ignore repos with a gl-creater file, as they are clones/scratch
    fi
done

if [ "$DATA" != "" ]; then
    echo -e $DATA | mail -r "sysadmin@kde.org" -s "Git repository hooks-disabled check" sysadmin@kde.org
fi
