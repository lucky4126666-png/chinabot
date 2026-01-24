# 用一个体积小的 Python 3.11 基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目全部代码
COPY . .

# 避免 Python 输出被缓冲
ENV PYTHONUNBUFFERED=1

# 容器启动时执行的命令（运行你的机器人）
CMD ["python", "bot.py"]
