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
    
    git commit -m "Record change: `cat - | jq -r '.NewImage | keys | .[]'`"

    # If there's a remote and we've committed changes, push
    if [ "`git remote`" != "" ]
    then 
        git push -q
    fi
fi