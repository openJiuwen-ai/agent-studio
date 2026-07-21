ARG GRAFANA_VERSION=11.3.0
FROM --platform=$BUILDPLATFORM grafana/grafana:${GRAFANA_VERSION} AS plugin-downloader

ARG VICTORIA_LOGS_DATASOURCE_VERSION=0.29.0

ENV GF_PATHS_PLUGINS=/usr/share/grafana/plugins
USER root
RUN mkdir -p "${GF_PATHS_PLUGINS}" && chown grafana:root "${GF_PATHS_PLUGINS}"
USER grafana
RUN grafana cli \
    --pluginsDir "${GF_PATHS_PLUGINS}" \
    plugins install victoriametrics-logs-datasource "${VICTORIA_LOGS_DATASOURCE_VERSION}"

FROM grafana/grafana:${GRAFANA_VERSION}

# Bake the datasource into the image so Grafana startup never depends on
# grafana.com or the plugin catalog being reachable. Keep it outside
# /var/lib/grafana because that path is covered by Grafana's data volume.
ENV GF_PATHS_PLUGINS=/usr/share/grafana/plugins
ENV GF_ANALYTICS_CHECK_FOR_UPDATES=false \
    GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false \
    GF_PLUGINS_PREINSTALL_DISABLED=true \
    GF_PLUGINS_PLUGIN_ADMIN_ENABLED=false

USER root
RUN mkdir -p "${GF_PATHS_PLUGINS}" && chown grafana:root "${GF_PATHS_PLUGINS}"
COPY --from=plugin-downloader --chown=grafana:root \
    /usr/share/grafana/plugins/ /usr/share/grafana/plugins/
USER grafana
