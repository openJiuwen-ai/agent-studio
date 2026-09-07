ARG BASE_IMAGE
FROM $BASE_IMAGE
RUN echo "Built on $BASE_IMAGE"

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y iproute2 libcap2-bin unzip && rm -rf /var/lib/apt/lists/*

RUN groupadd servicegroup && useradd -u 1001 -g servicegroup -m -s /bin/bash service

RUN mkdir -p /opt/cloud/wiseagent-nginx/nginx/sbin \
    && mkdir -p /opt/cloud/wiseagent-nginx/nginx/conf \
    && mkdir -p /opt/cloud/wiseagent-nginx/nginx/dist \
    && mkdir -p /opt/cloud/wiseagent-nginx/conf \
    && mkdir -p /opt/cloud/wiseagent-nginx/logs \
    && ln -s /usr/sbin/nginx /opt/cloud/wiseagent-nginx/nginx/sbin/nginx \
    && ln -s /etc/nginx/mime.types /opt/cloud/wiseagent-nginx/conf/mime.types \
    && ln -s /etc/nginx/mime.types /opt/cloud/wiseagent-nginx/nginx/conf/mime.types \
    && echo 'include /opt/cloud/wiseagent-nginx/conf/nginx.conf;' > /etc/nginx/nginx.conf \
    && mkdir -p /home/conf \
    && mkdir -p /home/secret

WORKDIR /home/service

ADD agent-console.tar /opt/cloud/wiseagent-nginx/nginx/
ADD script/start.sh ./

RUN chmod u+x start.sh \
    && chown -R 1001:1000 /opt/cloud/wiseagent-nginx \
    && chown -R 1001:1000 /home \
    && mkdir -p nginx/scc_data \
    && chown -R 1001:1000 nginx/scc_data \
    && mkfifo nginx/keypassfifo \
    && chown 1001:1000 nginx/keypassfifo \
    && chmod 600 nginx/keypassfifo \
    && setcap cap_net_bind_service=+eip /usr/sbin/nginx

EXPOSE 80 443

ENTRYPOINT ["/bin/bash","start.sh"]