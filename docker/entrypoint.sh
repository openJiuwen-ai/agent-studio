#!/bin/bash
set -e  

find /app -mindepth 1 -maxdepth 1 ! -name "site-packages" -exec chown -R app:app {} \;

for pathName in data openjiuwen_studio
do
  absPath="/app/site-packages/${pathName}"
  if [ -d "${absPath}" ]; then
    chown -R app:app ${absPath}
    chmod -R 644 ${absPath}
    echo "Updated ownership of ${absPath} to app:app"
  fi
done

exec su app -s /bin/sh -c 'export PYTHONPATH="$PYTHONPATH" PATH="$PATH"; exec "$@"' -- sh "$@"