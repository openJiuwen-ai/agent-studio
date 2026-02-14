#!/usr/bin/env bash
sort ../.env.example > .env.runtime.default
sed -i 's/#.*//; /^[[:space:]]*$/d' .env.runtime.default
sed -i -E 's/^[[:space:]]+//; s/[[:space:]]+$//' .env.runtime.default
sed -i '/^CODE_SANDBOX_URL=/d; /^DB_HOST=/d; /^MILVUS_HOST=/d; /^SERVER_AES_MASTER_KEY=/d; /^SSL_PASSWORD=/d; /^VITE_API_PROXY_TARGET=/d; /^VITE_PLUGIN_SERVICE_URL=/d; /^MINIO_HOST=/d; /^DEEPSEARCH_AGENT_HOST=/d' .env.runtime.default
sed -i 's/^DB_TYPE=.*/DB_TYPE=mysql/; s/^FRONTEND_PORT=.*/FRONTEND_PORT=3001/; s/^INDEX_MANAGER_TYPE=.*/INDEX_MANAGER_TYPE=milvus/;' .env.runtime.default

cp -rf ../backend/openjiuwen_studio/examples .
cp ../backend/openjiuwen_studio/conf/config.yaml conf/.
cp ../backend/openjiuwen_studio/conf/config.json conf/.
