# Skill 错误码说明

本文档整理 Skill 功能相关的错误码、默认错误信息、HTTP 状态码及建议处理方式，用于问题定位与接口联调。

## 错误码格式

Skill 相关错误码由后端 `StudioError` 枚举定义，完整错误码格式为：

```
openjiuwen.{模块子码}{4位错误码}
```

其中：

- `0200`（COMMON）为 Skill 导入、导出、校验等管理场景使用的错误码；
- `0210`（AGENT）为智能体关联 Skill 时使用的错误码。

错误码对应的默认错误信息由以下 i18n 文件提供：

- 中文：`backend/studio-common/src/main/resources/i18n/studio-messages_zh_CN.properties`
- 英文：`backend/studio-common/src/main/resources/i18n/studio-messages_en_US.properties`

## Skill 管理相关错误码（模块子码 0200）

| 完整错误码 | 枚举名称 | HTTP 状态码 | 默认错误信息 | 原因 | 处理建议 |
|------|------|------|------|------|------|
| openjiuwen.02001110 | SKILL_ID_IS_EMPTY | 400 | 缺少技能id。 | 技能id为空。 | 请检查技能id是否为空。 |
| openjiuwen.02001111 | SKILL_NOT_EXISTS | 400 | 缺少技能包。 | 技能不存在。 | 请检查技能包是否存在。 |
| openjiuwen.02001112 | SKILL_VERSION_IS_INCORRECT | 400 | 技能版本异常。 | 技能版本不存在。 | 请检查技能版本是否存在。 |
| openjiuwen.02001113 | OBS_URL_NOT_EXISTS | 400 | obs路径异常。 | obs路径不存在。 | 请检查obs路径是否存在。 |
| openjiuwen.02001114 | GET_OBS_TEMPORARY_URL_NOT_EXIST | 400 | 预签名obs路径异常。 | 预签名obs路径不存在。 | 请检查预签名obs路径是否存在。 |
| openjiuwen.02001115 | SKILL_MD_IS_MISSING | 400 | SKILL.md文件异常。 | SKILL.md文件不存在。 | 请检查SKILL.md文件是否存在。 |
| openjiuwen.02001116 | IO_ERROR | 400 | IO异常。 | 文件读取异常。 | 请重新上传文件。 |
| openjiuwen.02001117 | SKILL_ALREADY_EXIST | 400 | 技能已存在。 | 当前项目下已存在同ID的技能。 | 在重新创建之前删除已有的同ID技能。 |
| openjiuwen.02001121 | SKILL_SIZE_EXCEED_LIMIT | 400 | 文件大小超出限制。 | 文件大小超过了允许的最大值。 | 请使用较小的文件或压缩文件以减少其大小。 |
| openjiuwen.02001122 | ZIP_FILE_COUNT_EXCEED_LIMIT | 400 | 文件数量超出限制。 | ZIP文件中的条目数量超过了允许的最大值。 | 请减少ZIP文件中的文件数量或拆分为多个较小的ZIP文件。 |
| openjiuwen.02001123 | INSECURE_PATH | 400 | 文件名包含不安全路径。 | ZIP文件中包含路径穿越漏洞，使用了不安全的文件路径。 | 请使用安全的文件名，不包含"../"等特殊路径字符。 |
| openjiuwen.02001124 | UNSAFE_PATH | 400 | 文件包含符号链接。 | ZIP文件中包含符号链接，存在不安全的路径。 | 请确保ZIP文件中不包含任何符号链接，只使用常规文件。 |
| openjiuwen.02001125 | SKILL_MD_INVALID_FIELD | 400 | 元数据字段无效。 | 文件的前置元数据中包含了不在白名单中的无效字段。 | 请删除所有未授权的元数据字段，只保留系统允许的字段。 |
| openjiuwen.02001126 | NAME_FIELD_MISSING | 400 | 名称字段缺失。 | 在前置元数据中未找到必填的名称字段或该字段值为空。 | 请在元数据中添加有效的名称字段，确保其不为空。 |
| openjiuwen.02001127 | NAME_FORMAT_MISMATCH | 400 | 名称格式不符合规范 | SKILL包的名称字段(name)不满足格式要求。名称必须符合以下规则：1) 长度为1-64个字符；2) 只能包含小写字母(a-z)、数字(0-9)和连字符(-)；3) 必须以字母或数字开头和结尾，不能以连字符开头或结尾。 | 请检查SKILL.md文件中的name字段，确保符合命名规范。如果是目录名与name字段不一致的问题，请确保包含SKILL.md的目录名与frontmatter中的name字段完全一致。 |
| openjiuwen.02001128 | MAX_UPLOAD_SIZE_EXCEEDED | 400 | 上传大小超出最大限制。 | 上传文件大小超出系统最大限制。 | 请检查上传文件的大小。 |

## Agent 关联 Skill 相关错误码（模块子码 0210）

| 完整错误码 | 枚举名称 | HTTP 状态码 | 默认错误信息 | 原因 | 处理建议 |
|------|------|------|------|------|------|
| openjiuwen.02101049 | SKILL_NUM_EXCEED_LIMIT | 400 | Skill数量超过最大限制。 | Skill数量超过最大限制。 | 请减少Skill数量后重试。 |
| openjiuwen.02101050 | SKILL_NOT_EXIST | 404 | Skill不存在。 | Skill不存在。 | 请确认skill_id是否正确且存在。 |
| openjiuwen.02101051 | SKILL_VERSION_INVALID | 400 | Skill版本无效。 | Skill版本无效或不存在。 | 请确认当前Skill是否已启用对应版本。 |
| openjiuwen.02101052 | SKILL_ID_OR_VERSION_NOT_MATCH | 400 | Skill或版本不存在或不匹配。 | 指定的Skill或版本不存在或不符合预期配置。 | 请确保Skill、版本以及Skill配置正确无误。 |

## 参考来源

- 枚举定义：`backend/studio-common/src/main/java/com/openjiuwen/studio/agent/common/enums/StudioError.java`
- 中文错误信息：`backend/studio-common/src/main/resources/i18n/studio-messages_zh_CN.properties`
- 英文错误信息：`backend/studio-common/src/main/resources/i18n/studio-messages_en_US.properties`

> 说明：以上错误码与错误信息以后端枚举及 i18n 文件为单一来源，如代码更新，请同步更新本表。