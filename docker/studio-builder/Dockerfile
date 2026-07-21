ARG BASE_IMAGE
FROM $BASE_IMAGE

# 注：此处修改需同步修改studio-builder.yaml中的runAsUser、runAsGroup、fsGroup
RUN groupadd -g 1000 service && useradd -u 1000 -g service -s /bin/bash -m service

ENV SERVICE_HOME=/opt/cloud/agent-builder
ENV PACKAGES_HOME=/usr/local/lib/python3.11/site-packages
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib64

WORKDIR $SERVICE_HOME

# 安装运行时依赖（不含 nginx/iptables/cron —— builder 不运行负载均衡与定时任务；
# 保留 libpq-dev：agent_builder/requirements.txt 中的 py-opengauss 安装时需要）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; \
    fi \
    && apt-get update && apt-get install -y curl tar unzip net-tools wget libpq-dev vim procps gawk hostname sed coreutils findutils bash \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt，单独安装依赖以利用 Docker 层缓存
COPY agent_builder/requirements.txt $SERVICE_HOME/app/agent_builder/requirements.txt
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip3 config set global.trusted-host mirrors.aliyun.com \
    && pip3 install -r $SERVICE_HOME/app/agent_builder/requirements.txt \
    && rm -rf ${PACKAGES_HOME}/future/backports/test

# openjiuwen 不再从本地 agent-core 安装，改由 requirements.txt 从 PyPI(aliyun) 装 openjiuwen==0.1.16

# 再复制应用代码（变更频率高，放在依赖安装之后）
# 注意：studio-builder 镜像不包含 agent_runtime / jiuwen —— agent_builder 已与运行时解耦，
# 用本地 adapter（adapter.jiuwen_bridge 等）替代 jiuwen 包
COPY agent_builder/ $SERVICE_HOME/app/agent_builder/
# 共享包 model_service / storage：agent_builder 运行时 import，靠 PYTHONPATH=${SERVICE_HOME}/app 解析
COPY model_service/ $SERVICE_HOME/app/model_service/
COPY storage/ $SERVICE_HOME/app/storage/

# 启动脚本（init.sh / start.sh / start_server.sh）—— 参考 studio-runtime 启动模式
COPY script/ $SERVICE_HOME/script/

# 设置目录与权限
RUN mkdir -p /opt/cloud/logs \
    && mkdir -p /opt/cloud/tool \
    && mkdir -p /opt/tmp/agent \
    && mkdir -p /opt/cloud/logs/agent-builder/run \
    && touch /opt/cloud/logs/agent-builder/run/agent-builder.pid \
    && chmod 750 -R /opt/cloud/logs \
    && chmod +x $SERVICE_HOME/script/*.sh \
    && chmod u+w ${PACKAGES_HOME} \
    && chown -R service:service ${PACKAGES_HOME} \
    && chmod 700 $SERVICE_HOME/.. \
    && chown -R service:service /home \
    && chown -R service:service /opt/cloud \
    && chown -R service:service /opt/tmp/agent \
    && chmod 755 /home

USER service

ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=31015

# 参考 studio-runtime：先 init.sh（目录/TLS），再 start.sh（nohup 拉起服务 + 主循环保活）
CMD ["/bin/bash", "-c", "cd ${SERVICE_HOME}; ./script/init.sh; exec ./script/start.sh"]
