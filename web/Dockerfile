FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Scrapling 浏览器依赖
RUN scrapling install || true

# 复制代码
COPY crawler/ crawler/
COPY analysis/ analysis/
COPY data/ data/
COPY web/ web/
COPY run.py .

# 默认启动 API 服务
CMD ["python", "run.py", "api"]