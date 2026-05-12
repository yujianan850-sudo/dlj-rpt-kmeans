#!/bin/sh

set -e

# 容器名称
CONTAINER="zj_dlj-rpt-kmeans"
# 定义宿主机目录路径
HOST_DIR="/data/python/logs"
# 定义容器内目录路径
CONTAINER_DIR="/root/pythonlogs"
# 宿主机对外端口
SERVER_PORT="5001"
# 容器内服务端口
CONTAINER_PORT="5000"
# 镜像名称（以日期时间为镜像标签，防止重复）
IMAGE="${CONTAINER}:$(date -d "today" +"%Y%m%d_%H%M%S")"

# 删除当前容器对应的历史镜像
remove_old_images() {
    image_ids=$(docker images --format '{{.Repository}} {{.ID}}' | awk -v c="${CONTAINER}" '$1 ~ "^" c ":" {print $2}')
    if [ -n "${image_ids}" ]; then
        docker rmi --force ${image_ids}
    fi
}

# 查看容器状态
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

# 创建新镜像
docker build -t "${IMAGE}" .

# 启动服务
docker run -v "${HOST_DIR}:${CONTAINER_DIR}" -itd --name "${CONTAINER}" -p "${SERVER_PORT}:${CONTAINER_PORT}" --restart=always --log-opt max-size=50m --log-opt max-file=3 "${IMAGE}"
echo "${CONTAINER} 创建成功！"
