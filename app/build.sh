#!/bin/bash
# Usage: ./build.sh [dev|rc|rel]
# dev: development build
# rc: release candidate build
# rel: release build and push to ghcr.io
# Note: for release build, you need to set GHCR_TOKEN
# export GHCR_TOKEN=<YOUR_GITHUB_TOKEN> in your .zprofile
# see also: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry


set -e

BUILD_DATE=$(date -Iminutes)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
VERSION=$(git describe --tags --abbrev=0)
VERSION="${VERSION:1}"
arr=(${VERSION//./ })
MAJOR=${arr[0]}
IMAGE=tsun-gen3-proxy

if [[ $1 == debug ]] || [[ $1 == dev ]] ;then
IMAGE=docker.io/sallius/${IMAGE}
VERSION=${VERSION}-$1
elif [[ $1 == rc ]] || [[ $1 == rel ]];then
IMAGE=ghcr.io/s-allius/${IMAGE}
else
echo argument missing!
echo try: $0 '[debug|dev|rc|rel]'
exit 1
fi

echo version: $VERSION  build-date: $BUILD_DATE   image: $IMAGE
if [[ $1 == debug ]];then
docker build --build-arg "VERSION=${VERSION}" --build-arg environment=dev --build-arg "LOG_LVL=DEBUG" --label "org.opencontainers.image.created=${BUILD_DATE}" --label "org.opencontainers.image.version=${VERSION}" --label "org.opencontainers.image.revision=${BRANCH}" -t ${IMAGE}:debug app
elif [[ $1 == dev ]];then
docker build --build-arg "VERSION=${VERSION}" --build-arg environment=production --label "org.opencontainers.image.created=${BUILD_DATE}" --label "org.opencontainers.image.version=${VERSION}" --label "org.opencontainers.image.revision=${BRANCH}" -t ${IMAGE}:dev app

elif [[ $1 == rc ]];then
docker build --build-arg "VERSION=${VERSION}" --build-arg environment=production --label "org.opencontainers.image.created=${BUILD_DATE}" --label "org.opencontainers.image.version=${VERSION}" --label "org.opencontainers.image.revision=${BRANCH}" -t ${IMAGE}:rc -t ${IMAGE}:${VERSION} app
echo 'login to ghcr.io'    
echo $GHCR_TOKEN | docker login ghcr.io -u s-allius --password-stdin
docker push -q ghcr.io/s-allius/tsun-gen3-proxy:rc
docker push -q ghcr.io/s-allius/tsun-gen3-proxy:${VERSION}

elif [[ $1 == rel ]];then
docker build --no-cache --build-arg "VERSION=${VERSION}" --build-arg environment=production --label "org.opencontainers.image.created=${BUILD_DATE}" --label "org.opencontainers.image.version=${VERSION}" --label "org.opencontainers.image.revision=${BRANCH}" -t ${IMAGE}:latest -t ${IMAGE}:${MAJOR} -t ${IMAGE}:${VERSION} app
echo 'login to ghcr.io'    
echo $GHCR_TOKEN | docker login ghcr.io -u s-allius --password-stdin
docker push -q ghcr.io/s-allius/tsun-gen3-proxy:latest
docker push -q ghcr.io/s-allius/tsun-gen3-proxy:${MAJOR}
docker push -q ghcr.io/s-allius/tsun-gen3-proxy:${VERSION}
fi

echo 'check docker-compose.yaml file'
docker-compose config -q