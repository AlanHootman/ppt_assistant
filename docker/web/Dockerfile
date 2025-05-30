# 使用Node.js镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 设置环境变量
ARG NODE_ENV=development
ENV NODE_ENV=${NODE_ENV}
ENV CHOKIDAR_USEPOLLING=true
ENV HOST=0.0.0.0

ARG DOCKER_ENV
ENV VITE_DOCKER_ENV=$DOCKER_ENV

# 设置npm镜像源提高下载速度
RUN npm config set registry https://registry.npmmirror.com/

# 复制package文件
COPY apps/web/package*.json ./

# 安装依赖（添加重试机制和超时设置）
RUN npm ci --legacy-peer-deps

# 复制源代码
COPY apps/web/ ./

# 构建生产版本（如果是生产环境）
RUN if [ "$NODE_ENV" = "production" ]; then npm run build; fi

# 暴露开发服务器端口
EXPOSE 5173

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5173/ || exit 1

# 启动服务
# 生产环境使用preview，开发环境使用dev
CMD if [ "$NODE_ENV" = "production" ]; then npm run preview; else npm run dev; fi 