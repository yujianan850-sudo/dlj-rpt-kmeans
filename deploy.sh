#!/bin/bash

# 容器名称
CONTAINER="dlj-rpt-kmeans"
# 定义宿主机目录路径
HOST_DIR="/data/python/logs"
# 定义容器内目录路径
CONTAINER_DIR="/root/pythonlogs"
# 容器主服务对外端口
SERVER_PORT="5000"
# 镜像名称（以日期时间为镜像标签，防止重复）
IMAGE=$CONTAINER":"$(date -d "today" +"%Y%m%d_%H%M%S")
# 查看容器是否状态
STATUS=`docker inspect --format '{{.State.Status}}' ${CONTAINER}`
echo ${STATUS}

if [ ${STATUS} = "running" ]
then {
        # 停止容器
        docker stop `docker ps | grep -w $CONTAINER | awk '{print $1}'` && \
        # 删除容器
        docker rm `docker ps -a | grep -w $CONTAINER | awk '{print $1}'` && \
        # 强制除镜像
        docker rmi --force `docker images | grep -w $CONTAINER | awk '{print $3}'`
}
elif [ ${STATUS} = "exited" ]
then {
        # 删除容器
        docker rm `docker ps -a | grep -w $CONTAINER | awk '{print $1}'` && \
        # 强制除镜像
        docker rmi --force `docker images | grep -w $CONTAINER | awk '{print $3}'`
}
else
{
        # 强制除镜像
        docker rmi --force `docker images | grep -w $CONTAINER | awk '{print $3}'`
}
fi
# 创建新镜像
docker build -t $IMAGE .&& \

# 启动服务
docker run -v $HOST_DIR:$CONTAINER_DIR -itd --name $CONTAINER -p $SERVER_PORT:$SERVER_PORT --restart=always --log-opt max-size=50m --log-opt max-file=3 $IMAGE
echo "${CONTAINER}创建成功！"


