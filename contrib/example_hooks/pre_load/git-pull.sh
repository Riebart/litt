#!/bin/bash

# Assumes that there is a git repository in ~/.litt (that is, ~/.litt/.git exists), and before every
# load of the db file, it fetches from the git repo using `git pull`.
#
# Merge conflicts result in a non-zero exit code, causing the tt operation to abort.
#
# Depends on: git

set -e

if [ "`git remote`" != "" ] # If there's a remote, try to pull
then 
    git pull -q
fi
