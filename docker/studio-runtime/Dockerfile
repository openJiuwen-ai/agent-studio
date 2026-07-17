ARG BASE_IMAGE
FROM $BASE_IMAGE

# 注：此处修改需同步修改studio-runtime.yaml中的runAsUser、runAsGroup、fsGroup
RUN groupadd -g 1000 service && useradd -u 1000 -g service -s /bin/bash -m service

ENV SERVICE_HOME=/opt/cloud/agent-runtime
ENV PACKAGES_HOME=/usr/local/lib/python3.11/site-packages
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib64

WORKDIR $SERVICE_HOME

# 安装运行时依赖（不含编译工具链）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list; \
    fi \
    && apt-get update && apt-get install -y curl tar unzip net-tools wget iptables cron libpq-dev vim procps gawk hostname sed coreutils findutils bash nginx antiword \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 先复制 requirements.txt，单独安装依赖以利用 Docker 层缓存
COPY requirements.txt $SERVICE_HOME/app/
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && pip3 config set global.trusted-host mirrors.aliyun.com \
    && pip3 install -r $SERVICE_HOME/app/requirements.txt \
    && rm -rf ${PACKAGES_HOME}/future/backports/test

# 再复制应用代码（变更频率高，放在依赖安装之后）
# 注：agent_builder 已从 studio-runtime 镜像剥离，独立构建为 studio-builder 镜像
COPY agent_runtime/ $SERVICE_HOME/app/agent_runtime/
COPY jiuwen/ $SERVICE_HOME/app/jiuwen/
COPY model_service/ $SERVICE_HOME/app/model_service/
COPY storage/ $SERVICE_HOME/app/storage/
COPY tests/ $SERVICE_HOME/app/tests/
COPY bin/ $SERVICE_HOME/bin/
# Nginx load balancing configuration and scripts
COPY nginx/ $SERVICE_HOME/nginx/

# 设置目录与权限
RUN mkdir -p $SERVICE_HOME/bin \
    && chmod +x $SERVICE_HOME/bin/*.sh \
    && chmod +x $SERVICE_HOME/nginx/nginx_launcher.py \
    && mkdir -p $SERVICE_HOME/tls \
    && mkdir -p /opt/cloud/logs \
    && mkdir -p /opt/cloud/tool \
    && mkdir -p /opt/tmp/agent \
    && mkdir -p /opt/cloud/logs/agent-runtime/run \
    && touch /opt/cloud/logs/agent-runtime/run/agent-runtime.pid \
    && touch /opt/cloud/logs/agent-runtime/run/agent-runtime_access.log \
    && touch /opt/cloud/logs/agent-runtime/run/agent-runtime_debug.log \
    && chmod 750 -R /opt/cloud/logs $SERVICE_HOME/tls/ \
    && chmod u+w ${PACKAGES_HOME} \
    && chown -R service:service ${PACKAGES_HOME} \
    && chmod 700 $SERVICE_HOME/.. \
    && chown -R service:service /home \
    && chown -R service:service /opt/cloud \
    && chown -R service:service /opt/tmp/agent \
    && chmod 755 /home

# 定义定时任务需要的权限 + Nginx 运行时目录权限
USER root
RUN chmod 700 /opt/cloud/logs \
    && echo service >> /etc/cron.allow \
    && chmod u+s /usr/sbin/cron \
    && touch /var/run/crond.pid && chmod 760 /var/run/crond.pid \
    && mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi /var/lib/nginx/uwsgi /var/lib/nginx/scgi \
    && chown -R service:service /var/lib/nginx \
    && mkdir -p /var/log/nginx \
    && chown -R service:service /var/log/nginx \
    && touch /run/nginx.pid \
    && chown service:service /run/nginx.pid

USER service

CMD ["/bin/bash", "-c", "cron;cd ${SERVICE_HOME};./bin/init.sh; if [ \"${NGINX_LOAD_BALANCING}\" = \"true\" ]; then ./bin/start_nginx_lb.sh; else ./bin/start.sh; fi"]