ARG BASE_IMAGE
FROM $BASE_IMAGE
RUN echo "Built on $BASE_IMAGE" \
    && if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
         sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
       elif [ -f /etc/apt/sources.list ]; then \
         sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; \
       fi \
    && apt-get update && apt-get install -y vim unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 注：此处修改需同步修改studio-manager.yaml中的runAsUser、runAsGroup、fsGroup
RUN groupadd -g 1001 service && useradd -u 1001 -g service -s /bin/bash -m service

# 根路径
ARG APP_PATH=/opt/cloud/studio-manager
ENV APP_PATH $APP_PATH

WORKDIR ${APP_PATH}

# 拷贝
COPY lib/*.jar app/
COPY script/ bin/
COPY config/ config/

# 赋权
RUN mkdir -p logs \
    && chmod -R 550 app/ \
    && chmod -R 750 bin/ config/ logs/ \
    && chown -R service:service app/ bin/ config/ logs/

# 切换到非 root 用户运行
USER service

# 暴露 Spring Boot 默认端口
EXPOSE 31111

# 使用启动脚本作为入口点，确保信号传递到 Java 进程
ENTRYPOINT ["bin/start.sh"]