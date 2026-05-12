FROM python:3.7.0

WORKDIR /app

ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1
ENV OUTPUT_DIR=/app/output
ENV WINDOW_DAYS=15
ENV RETRAIN_INTERVAL_DAYS=7
ENV WORKER_THREADS=5
ENV MAX_TRAIN_COUNT=-1
ENV MONGO_HOST=172.22.22.120
ENV MONGO_PORT=27017
ENV MONGO_AUTH_DB=admin
ENV MONGO_TARGET_DB=galv-center

COPY requirements.txt /app/requirements.txt

ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=10

RUN python -c "import urllib.request; urllib.request.urlretrieve('https://bootstrap.pypa.io/pip/3.7/get-pip.py', '/tmp/get-pip.py')" && \
    python /tmp/get-pip.py && \
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    "setuptools<70" wheel && \
    python -m pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    --retries 10 --timeout 120 -r /app/requirements.txt

COPY incremental_train.py /app/
RUN mkdir -p /app/output /app/logs

CMD ["python", "incremental_train.py"]
