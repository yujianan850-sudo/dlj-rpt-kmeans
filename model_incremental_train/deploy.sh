#!/bin/sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER="zj_dlj-incremental-train"
HOST_OUTPUT_DIR="${SCRIPT_DIR}/output"
HOST_LOG_DIR="${SCRIPT_DIR}/logs"
CONTAINER_OUTPUT_DIR="/app/output"
CONTAINER_LOG_DIR="/app/logs"
IMAGE="${CONTAINER}:$(date +"%Y%m%d_%H%M%S")"

MONGO_HOST="${MONGO_HOST:-172.22.22.120}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_USER="${MONGO_USER:-guiwu}"
MONGO_PWD="${MONGO_PWD:-106ling106}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"
MONGO_TARGET_DB="${MONGO_TARGET_DB:-galv-center}"
WINDOW_DAYS="${WINDOW_DAYS:-15}"
RETRAIN_INTERVAL_DAYS="${RETRAIN_INTERVAL_DAYS:-7}"
WORKER_THREADS="${WORKER_THREADS:-5}"
MAX_TRAIN_COUNT="${MAX_TRAIN_COUNT:--1}"
TRAIN_U_WAVE_OVERRIDE="${TRAIN_U_WAVE_OVERRIDE:-0.05}"
RUN_END_DATE_OVERRIDE="${RUN_END_DATE_OVERRIDE:-}"

remove_old_images() {
    image_ids=$(docker images --format '{{.Repository}} {{.ID}}' | awk -v c="${CONTAINER}" '$1 ~ "^" c ":" {print $2}')
    if [ -n "${image_ids}" ]; then
        docker rmi --force ${image_ids}
    fi
}

mkdir -p "${HOST_OUTPUT_DIR}" "${HOST_LOG_DIR}"

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

docker build -t "${IMAGE}" "${SCRIPT_DIR}"

docker run -d \
  --name "${CONTAINER}" \
  --restart=always \
  --log-opt max-size=50m \
  --log-opt max-file=3 \
  -v "${HOST_OUTPUT_DIR}:${CONTAINER_OUTPUT_DIR}" \
  -v "${HOST_LOG_DIR}:${CONTAINER_LOG_DIR}" \
  -e MONGO_HOST="${MONGO_HOST}" \
  -e MONGO_PORT="${MONGO_PORT}" \
  -e MONGO_USER="${MONGO_USER}" \
  -e MONGO_PWD="${MONGO_PWD}" \
  -e MONGO_AUTH_DB="${MONGO_AUTH_DB}" \
  -e MONGO_TARGET_DB="${MONGO_TARGET_DB}" \
  -e WINDOW_DAYS="${WINDOW_DAYS}" \
  -e RETRAIN_INTERVAL_DAYS="${RETRAIN_INTERVAL_DAYS}" \
  -e WORKER_THREADS="${WORKER_THREADS}" \
  -e MAX_TRAIN_COUNT="${MAX_TRAIN_COUNT}" \
  -e TRAIN_U_WAVE_OVERRIDE="${TRAIN_U_WAVE_OVERRIDE}" \
  -e RUN_END_DATE_OVERRIDE="${RUN_END_DATE_OVERRIDE}" \
  -e OUTPUT_DIR="${CONTAINER_OUTPUT_DIR}" \
  -e LOG_DIR="${CONTAINER_LOG_DIR}" \
  "${IMAGE}"

echo "${CONTAINER} 创建成功！"
echo "Excel 输出目录: ${HOST_OUTPUT_DIR}"
echo "运行日志目录: ${HOST_LOG_DIR}"
echo "重训间隔: ${RETRAIN_INTERVAL_DAYS} 天，首训窗口: ${WINDOW_DAYS} 天"
