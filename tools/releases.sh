#!/bin/bash

set -e

# notes
## git cherry-pick <sha-of-bump-version>..master

RELEASE=6.2.0
BRANCH=6.2
PYTHON_VERSION=3.9

REPO=git@github.com:errbotio/errbot.git
# REPO=/Users/saviles/data/git/sijis/errbot

RELEASE_DIR=$(mktemp -d /tmp/errbot-release-${RELEASE}.XXX)


function header () {
    title=$@
    ORANGE='\033[0;33m'
    YELLOW='\033[1;33m'
    NC='\033[0m'

    echo -e "${YELLOW}=================="
    echo -e "${ORANGE}${title}"
    echo -e "${YELLOW}=================="
    echo -e ${NC}
}


header "git clone"
pushd ${RELEASE_DIR}
git clone ${REPO} errbot
pushd errbot
git checkout ${BRANCH}

header "pypi build"
pipenv --python ${PYTHON_VERSION}
pipenv run pip3 install pytest twine build

header "pre-release gate (version <-> CHANGES.rst)"
pipenv run python3 -m pytest tests/release_metadata_test.py -v

pipenv run python3 -m build

header "docker build"
# docker build -t errbot:release-test .
docker buildx build --push --platform linux/amd64,linux/arm64/v8 -t errbotio/errbot:${RELEASE} -f Dockerfile .

header "publish: git tag, docs, version files"
pipenv run twine check dist/*

echo pipenv run twine upload dist/*
echo docker push tag errbot:release-test errbotio/errbot:${RELEASE}
echo docker push errbotio/errbot:${RELEASE}

popd
popd