FROM nginx:alpine

# 安装curl和netcat用于健康检查和服务等待
RUN apk add --no-cache curl netcat-openbsd

# 复制nginx配置文件
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# 复制等待脚本
COPY nginx/wait-for-services.sh /usr/local/bin/wait-for-services.sh

# 复制nginx主配置（如果需要自定义）
# COPY nginx/nginx.conf /etc/nginx/nginx.conf

# 设置权限
RUN chmod 644 /etc/nginx/conf.d/default.conf \
    && chmod +x /usr/local/bin/wait-for-services.sh

# 创建日志目录
RUN mkdir -p /var/log/nginx

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# 暴露端口
EXPOSE 80 443

# 使用等待脚本启动Nginx
CMD ["/usr/local/bin/wait-for-services.sh"] 