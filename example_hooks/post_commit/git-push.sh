#!/bin/bash

# Assumes that there is a git repository in ~/.litt (that is, ~/.litt/.git exists), and after every
# commit to the local filesystem it commits with the description and detail (if they exist) and then
# pushes.
#
# Depends on: git, jq, tr

set -e

git add events.json config.json
git commit -m "`date +%F_%T`"

if [ "`git remote`" != "" ] # If there's a remote, try to pull
then 
    git push -q
fi
