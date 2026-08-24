#!/usr/bin/env python3
# zip_platform.py — 平台专用打包助手（build.ps1 / build.sh 共用，排除规则单一真相源）
#
# 用法: python zip_platform.py <staging_abs> <out_zip_abs> <win|linux>
#
# 遍历 staging，按平台**排除**对端依赖 + MySQL 冗余 + 对端 wheel，写正斜杠 arcname 的
# ZIP_DEFLATED zip。避免复制 4GB staging 两次。排除规则见同目录 build.ps1/build.sh 注释。

import logging
import os
import sys
import zipfile


def kept_for_platform(rel, platform):
    """
    rel: 相对 staging 的正斜杠路径（如 deps/win/mysql-8.0/bin/mysqld.pdb）。
    返回 True=写入 zip，False=排除。
    """
    parts = rel.split('/')
    # 保险：排除构建期临时/产物（本不在 staging，防御性）
    top = parts[0] if parts else ''
    if top in ('build', 'dist', '.cache'):
        return False

    # 运行时生成的目录——干净安装包不得携带已用状态（如目标机首启前的 venv、
    # mysql/redis/minio 数据、服务日志、pid/temp）。start 脚本会 mkdir -p 重建它们。
    # 防御性排除：即便在用过的 staging 上打包也不会把 venv/data/logs 打进包。
    if top in ('run', 'data', 'logs', 'temp'):
        return False

    # 前端 sourcemap（*.map）—— prod 运行时无用，浏览器 devtools 调试用，瘦身去之
    fname = parts[-1] if parts else ''
    if fname.endswith('.map') and 'frontend' in parts:
        return False

    # Python 缓存目录（__pycache__）——工作区的 .pyc 是构建机解释器版本（如 cp312）产物，
    # 与本包内置 cp311 运行时版本不符，属垃圾且可能误导；运行时按版本忽略并自动重建。
    if '__pycache__' in parts:
        return False

    # 1) 对端平台依赖目录整体排除
    if len(parts) >= 2 and parts[0] == 'deps':
        other = 'linux' if platform == 'win' else 'win'
        if parts[1] == other:
            return False

        # 2) MySQL 冗余（仅本平台 deps/<plat>/mysql-8.0/...）
        if len(parts) >= 3 and parts[1] == platform and parts[2] == 'mysql-8.0':
            name = parts[-1]
            # 调试符号（win 445MB）+ 开发导入库（win 42MB）—— 运行时无用
            if name.endswith('.pdb') or name.endswith('.lib'):
                return False
            # mecab 日文字典：保留 utf-8 兜底现代日文，去掉 euc-jp/sjis 遗留编码（省 ~80MB/平台）
            # 路径形如 deps/<plat>/mysql-8.0/lib/mecab/dic/ipadic_euc-jp/sys.dic
            if len(parts) >= 7 and parts[3:6] == ['lib', 'mecab', 'dic']:
                dic = parts[6]
                if dic in ('ipadic_euc-jp', 'ipadic_sjis'):
                    return False

        # 3) Python wheels 按平台标签过滤（deps/wheels/*.whl）
        if len(parts) >= 2 and parts[1] == 'wheels':
            name = parts[-1]
            if name.endswith('.whl'):
                # wheel 文件名末段（平台标签）：...-cp311-...-<plat>.whl 或 ...-py3-none-any.whl
                lower = name.lower()
                is_any = lower.endswith('-none-any.whl') or lower.endswith('-py2.py3-none-any.whl') \
                         or '-none-any.whl' in lower
                if is_any:
                    return True  # 纯 python，两平台共享
                if platform == 'win':
                    return ('win_amd64' in lower) or ('win32' in lower) or ('_win.whl' in lower) \
                           or lower.endswith('-win.whl')
                else:  # linux
                    return ('manylinux' in lower) or ('linux_' in lower) or ('-linux' in lower)
            # 非 .whl 文件一律保留
    return True


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    if len(sys.argv) != 4:
        logging.error("用法: python zip_platform.py <staging_abs> <out_zip_abs> <win|linux>")
        sys.exit(2)
    staging, out_zip, platform = sys.argv[1], sys.argv[2], sys.argv[3].lower()
    if platform not in ('win', 'linux'):
        logging.error("platform 须为 win 或 linux，得到: %s", platform)
        sys.exit(2)
    if not os.path.isdir(staging):
        logging.error("staging 不存在: %s", staging)
        sys.exit(1)

    kept = 0
    excluded = 0
    staging = os.path.abspath(staging)
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for root, dirs, files in os.walk(staging):
            # 排序仅保证可读性
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, staging).replace(os.sep, '/')
                if kept_for_platform(rel, platform):
                    z.write(full, rel)
                    kept += 1
                else:
                    excluded += 1
    logging.info("[%s] wrote %d entries, excluded %d -> %s (%.1f MB)",
                 platform, kept, excluded, out_zip, os.path.getsize(out_zip) / 1048576.0)


if __name__ == '__main__':
    main()
