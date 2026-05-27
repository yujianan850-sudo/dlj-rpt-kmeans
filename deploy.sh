#!/bin/sh

set -e

# 主业务 API 容器（FastAPI + 定时机时），不是增量训练容器
CONTAINER="zj_dlj-rpt-kmeans"
HOST_DIR="/data/python/logs"
CONTAINER_DIR="/root/pythonlogs"
SERVER_PORT="5001"
CONTAINER_PORT="5000"
IMAGE="${CONTAINER}:$(date +"%Y%m%d_%H%M%S")"

remove_old_images() {
    image_ids=$(docker images --format '{{.Repository}} {{.ID}}' | awk -v c="${CONTAINER}" '$1 ~ "^" c ":" {print $2}')
    if [ -n "${image_ids}" ]; then
        docker rmi --force ${image_ids}
    fi
}

if docker inspect "${CONTAINER}" >/dev/null 2>&1; then
    STATUS=$(docker inspect --format '{{.State.Status}}' "${CONTAINER}")
    echo "${STATUS}"
    if [ "${STATUS}" = "running" ]; then
        docker stop "${CONTAINER}"
        docker rm "${CONTAINER}"
        remove_old_images
    elif [ "${STATUS}" = "exited" ]; then
        docker rm "${CONTAINER}"
        remove_old_images
    else
        docker rm -f "${CONTAINER}"
        remove_old_images
    fi
else
    echo "容器不存在，跳过清理"
    remove_old_images
fi

docker build -t "${IMAGE}" .

docker run -v "${HOST_DIR}:${CONTAINER_DIR}" -itd \
  --name "${CONTAINER}" \
  -p "${SERVER_PORT}:${CONTAINER_PORT}" \
  --restart=always \
  --log-opt max-size=50m \
  --log-opt max-file=3 \
  "${IMAGE}"

echo "${CONTAINER} 创建成功！"
echo "主业务 API: 0.0.0.0:${SERVER_PORT} -> 容器 ${CONTAINER_PORT}"
echo "增量训练请使用: model_incremental_train/deploy.sh"
