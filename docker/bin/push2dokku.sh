#!/bin/bash
set -exo pipefail

BIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source $BIN_DIR/set_git_env_vars.sh

pushd $(mktemp -d)
git init
echo "FROM mozorg/bedrock_demo:${GIT_COMMIT}" > Dockerfile
git add Dockerfile
git commit -m 'Add Dockerfile'

ssh -t dokku-demos -- apps:clone --ignore-existing --skip-deploy bedrock "$CI_ENVIRONMENT_SLUG"
git push -f ssh://dokku-demos:22/$CI_ENVIRONMENT_SLUG
ssh -t dokku-demos -- letsencrypt:auto-renew $CI_ENVIRONMENT_SLUG
