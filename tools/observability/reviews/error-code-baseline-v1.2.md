# Studio 2.0 错误码基线评审记录

## 评审结论

- 治理目标分支：`studio-2.0-dev`
- 协议版本：`v1.2`
- 初始源码基线提交：`4d21655300ea789b1b1e38141b7761acefb9ee69`
- 候选总数：1506；已登记 definition：846；已登记跨服务 reference：4；未登记候选：660
- `0200`～`0240`、`0260`～`0320` 已冻结；`0250`、`0330` 暂定；`1210` 预留
- Runtime 已验证的精确对外值 `openjiuwen.121007` 作为 `legacy_other` 例外登记

未登记候选不代表允许继续新增或复用。现有问题以 `error-code-advisory-baseline.json` 的稳定指纹记录为 `accepted_existing`，须在切换阻断式治理前按 Owner 和目标里程碑处理。

## 维护规则

Manifest 是错误码治理事实源，可读目录由脚本生成。刷新存量基线时，当前三服务源码树必须与 `studio-2.0-dev` 一致，且基线刷新不得与三服务源码修改处于同一变更中：

```bash
python3 tools/observability/scripts/check_error_code_inventory.py \
  --write-baseline --target-branch studio-2.0-dev
```

当前治理 Owner 为 `@zhuyechen`；合入团队仓库前，应按实际长期维护职责评估是否增加或替换 Owner。
