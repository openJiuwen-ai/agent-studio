ARG BASE_IMAGE
FROM $BASE_IMAGE
RUN echo "Built on $BASE_IMAGE"

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y iproute2 procps unzip && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 servicegroup && useradd -u 1001 -g servicegroup -m -s /bin/bash service

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
    && mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi /var/lib/nginx/uwsgi /var/lib/nginx/scgi \
    && chown -R 1001:1000 /var/lib/nginx \
    && mkdir -p /var/log/nginx \
    && chown -R 1001:1000 /var/log/nginx \
    && mkdir -p /var/cache/nginx \
    && chown -R 1001:1000 /var/cache/nginx \
    && touch /run/nginx.pid \
    && chown 1001:1000 /run/nginx.pid \
    && touch /opt/cloud/wiseagent-nginx/logs/access.log /opt/cloud/wiseagent-nginx/logs/error.log \
    && chown 1001:1000 /opt/cloud/wiseagent-nginx/logs/access.log /opt/cloud/wiseagent-nginx/logs/error.log \
    && chmod 640 /opt/cloud/wiseagent-nginx/logs/access.log /opt/cloud/wiseagent-nginx/logs/error.log

USER 1001:1000

EXPOSE 8080 8443

ENTRYPOINT ["/bin/bash","start.sh"]