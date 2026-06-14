#!/bin/bash

set -e

# notes
## git cherry-pick <sha-of-bump-version>..master
## git tag
## git push upstream ${BRANCH}

RELEASE=6.2.1
BRANCH=6.2
PYTHON_VERSION=3.12

REPO=git@github.com:errbotio/errbot.git

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

#header "pre-release gate (version <-> CHANGES.rst)"
#pipenv run python3 -m pytest tests/release_metadata_test.py -v

pipenv run python3 -m build

header "Building multi-arch docker images..."
podman rmi -f errbotio/errbot:test 2>/dev/null || true
podman manifest rm errbotio/errbot:test 2>/dev/null || true
podman build --platform linux/amd64,linux/arm64 --manifest errbotio/errbot:test -f Dockerfile .

header "Checking and uploading Python package..."
pipenv run twine check dist/*

header "Manual: publish pypi and docker"
echo pipenv run twine upload dist/*
echo podman build --platform linux/amd64,linux/arm64 --manifest errbotio/errbot:${RELEASE} -f Dockerfile .
echo podman manifest push errbotio/errbot:${RELEASE} docker://docker.io/errbotio/errbot:${RELEASE}
echo git tag v${RELEASE}

popd
popd
