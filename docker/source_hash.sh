#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"

if ! command -v git >/dev/null 2>&1 || [ ! -d "${WORKSPACE}/.git" ]; then
  exit 2
fi

cd "${WORKSPACE}"
SOURCE_PATHS=(
  backend frontend agent-runtime agent_builder packages/model_service packages/storage packages/common_utils
  docker/package.sh docker/source_hash.sh
  docker/studio-manager docker/studio-console docker/studio-runtime docker/studio-builder
)

file_list() {
  git ls-files -co --exclude-standard -- "${SOURCE_PATHS[@]}" | LC_ALL=C sort
}

# 同时纳入文件路径和工作区当前内容。git hash-object --stdin-paths 会读取工作区文件，
# 因而未提交修改也会改变指纹；批量计算避免为数千个文件逐个启动 sha256sum。
{
  file_list | sha256sum
  file_list | git hash-object --stdin-paths | sha256sum
} | sha256sum | cut -d' ' -f1
