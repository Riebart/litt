#!/bin/bash

# Assumes that there is a git repository in ~/.litt (that is, ~/.litt/.git exists), and after every
# commit to the local filesystem it commits with the description and detail (if they exist) and then
# pushes.
#
# Depends on: git, jq, tr

set -e

git add events.json config.json

# If there are changes to any tracked files, then commit.
if [ "`git status --untracked=no -s`" != "" ]
then
    # Read stdin and tell jq to get the keys from the new image (that is, the record ID)
    stdin=$(cat -)
    if [ "$stdin" != "" ]
    then
        message=$(echo "$stdin" | jq -r '. | objects | .NewImage | keys | .[]')
    fi

    # If, for whatever reason, there was no record ID, then just use the current date and time.
    if [ "$message" == "" ]
    then
        message=$(date +%F_%T)
    fi

    git commit -m "Record change: $message"

    # If there's a remote and we've committed changes, push
    if [ "`git remote`" != "" ]
    then 
        git push -q
    fi
fi