#!/usr/bin/env bash
sort ../.env.example > .env.runtime.default
sed -i 's/#.*//; /^[[:space:]]*$/d' .env.runtime.default
sed -i -E 's/^[[:space:]]+//; s/[[:space:]]+$//' .env.runtime.default

sed -i '/^CODE_SANDBOX_URL=/d' .env.runtime.default
sed -i '/^DB_HOST=/d' .env.runtime.default
sed -i '/^MILVUS_HOST=/d' .env.runtime.default
sed -i '/^SERVER_AES_MASTER_KEY=/d' .env.runtime.default
sed -i '/^SSL_PASSWORD=/d' .env.runtime.default
sed -i '/^VITE_API_PROXY_TARGET=/d' .env.runtime.default
sed -i '/^VITE_PLUGIN_SERVICE_URL=/d' .env.runtime.default
sed -i '/^MINIO_HOST=/d' .env.runtime.default
sed -i '/^DEEPSEARCH_AGENT_HOST=/d' .env.runtime.default
sed -i '/^DEEPSEARCH_AGENT_TELEMETRY_HOST=/d' .env.runtime.default
sed -i '/^RUNTIME_HOST=/d' .env.runtime.default

sed -i 's/^DB_TYPE=.*/DB_TYPE=mysql/' .env.runtime.default
sed -i 's/^FRONTEND_PORT=.*/FRONTEND_PORT=3001/' .env.runtime.default
sed -i 's/^INDEX_MANAGER_TYPE=.*/INDEX_MANAGER_TYPE=milvus/' .env.runtime.default
sed -i 's/^RUNTIME_PORT=.*/RUNTIME_PORT=8186/' .env.runtime.default

cp -rf ../backend/openjiuwen_studio/examples .
cp ../backend/openjiuwen_studio/conf/config.yaml conf/.
cp ../backend/openjiuwen_studio/conf/config.json conf/.
