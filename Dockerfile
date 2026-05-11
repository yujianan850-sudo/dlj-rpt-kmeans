# 使用 Python 官方镜像作为基础镜像
FROM python:3.7.0

# 设置工作目录
WORKDIR /app

# 复制应用程序代码到容器中
COPY . /app

ENV TMPDIR /data/galv-center/algorithm_python/pip_temp
# 创建临时目录
RUN mkdir -p $TMPDIR

ENV TZ=Asia/Shanghai

# 安装应用程序依赖项
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 暴露应用程序运行的端口
EXPOSE 5000
# 输出环境变量的值
RUN echo $PYTHONPATH
# 设置PYTHONPATH
ENV PYTHONPATH=/app

# 启动应用程序
CMD ["python", "main.py"]
