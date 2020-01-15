#!/bin/bash
set -exo pipefail

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh

pushd $(mktemp -d)
git init
echo "FROM mozorg/bedrock_demo:${GIT_COMMIT}" > Dockerfile
git add Dockerfile
git commit -m 'Add Dockerfile'

APP_NAME="www-${CI_COMMIT_REF_SLUG}"
ssh -t dokku@demos.moz.works -- apps:clone --ignore-existing --skip-deploy bedrock "$APP_NAME"
git push -f dokku@demos.moz.works:$APP_NAME master:refs/heads/master
ssh -t dokku@demos.moz.works -- letsencrypt:auto-renew $APP_NAME
