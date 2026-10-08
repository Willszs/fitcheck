FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 python 生成 pyc 缓存以及实时输出日志
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 安装系统时区依赖
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 Render 默认 Web 端口
EXPOSE 8080

# 启动 Bot & Web Service
CMD ["python", "bot.py"]

