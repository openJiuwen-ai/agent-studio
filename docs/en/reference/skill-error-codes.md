# Skill Error Codes

This document lists the error codes related to the Skill feature, along with their default messages, HTTP status codes, and suggested handling methods. It is intended for troubleshooting and API integration.

## Error Code Format

Skill-related error codes are defined by the backend `StudioError` enum. The full error code format is:

```
openjiuwen.{module sub-code}{4-digit error code}
```

- `0200` (COMMON) is used for Skill import, export, validation, and other management scenarios.
- `0210` (AGENT) is used when an agent references a Skill.

The default error messages are provided by the following i18n files:

- Chinese: `backend/studio-common/src/main/resources/i18n/studio-messages_zh_CN.properties`
- English: `backend/studio-common/src/main/resources/i18n/studio-messages_en_US.properties`

## Skill Management Error Codes (module sub-code 0200)

| Full Error Code | Enum Name | HTTP Status | Default Message | Reason | Suggestion |
|------|------|------|------|------|------|
| openjiuwen.02001110 | SKILL_ID_IS_EMPTY | 400 | The skill ID is missing. | The skill ID is empty. | Check whether the skill ID is empty. |
| openjiuwen.02001111 | SKILL_NOT_EXISTS | 400 | The skill package is missing. | The skill does not exist. | Check whether the skill package exists. |
| openjiuwen.02001112 | SKILL_VERSION_IS_INCORRECT | 400 | The skill version is abnormal. | The skill version does not exist. | Check whether the skill version exists. |
| openjiuwen.02001113 | OBS_URL_NOT_EXISTS | 400 | The OBS path is abnormal. | The OBS path does not exist. | Check whether the OBS path exists. |
| openjiuwen.02001114 | GET_OBS_TEMPORARY_URL_NOT_EXIST | 400 | The pre-signed OBS path is abnormal. | The pre-signed OBS path does not exist. | Check whether the pre-signed OBS path exists. |
| openjiuwen.02001115 | SKILL_MD_IS_MISSING | 400 | The SKILL.md file is abnormal. | The SKILL.md file does not exist. | Check whether the SKILL.md file exists. |
| openjiuwen.02001116 | IO_ERROR | 400 | I/O error. | An error occurred when reading the file. | Upload the file again. |
| openjiuwen.02001117 | SKILL_ALREADY_EXIST | 400 | The skill already exists. | A skill with the same id already exists in the current domain. | Delete the existing skill before creating it again. |
| openjiuwen.02001121 | SKILL_SIZE_EXCEED_LIMIT | 400 | File size exceeds the limit. | The file size exceeds the maximum allowed value. | Please use a smaller file or compress the file to reduce its size. |
| openjiuwen.02001122 | ZIP_FILE_COUNT_EXCEED_LIMIT | 400 | The number of files exceeds the limit. | The number of ZIP entries exceeds the maximum allowed count. | Please reduce the number of files in the ZIP archive or split it into multiple smaller ZIP files. |
| openjiuwen.02001123 | INSECURE_PATH | 400 | The file name contains an insecure path. | The ZIP file contains a path traversal vulnerability with an insecure file path. | Please use a secure file name without special path characters such as "../". |
| openjiuwen.02001124 | UNSAFE_PATH | 400 | The file contains symbolic links. | The ZIP file contains symbolic links, which creates unsafe paths. | Please ensure that the ZIP file does not contain any symbolic links and only uses regular files. |
| openjiuwen.02001125 | SKILL_MD_INVALID_FIELD | 400 | Invalid metadata field. | The frontmatter contains a field that is not in the allowed whitelist. | Please remove all unauthorized metadata fields and only keep the fields permitted by the system. |
| openjiuwen.02001126 | NAME_FIELD_MISSING | 400 | The name field is missing. | The required name field is missing from the frontmatter or its value is empty. | Please add a valid name field to the frontmatter and ensure it is not empty. |
| openjiuwen.02001127 | NAME_FORMAT_MISMATCH | 400 | Name format does not meet the specification | The name field in the SKILL package does not meet the format requirements. The name must comply with the following rules: 1) Length must be between 1 and 64 characters; 2) Can only contain lowercase letters (a-z), numbers (0-9), and hyphens (-); 3) Must start and end with a letter or number, and cannot start or end with a hyphen. | Please check the name field in the SKILL.md file to ensure it meets the naming specification. If the issue is that the directory name does not match the name field, please ensure that the directory containing SKILL.md has the exact same name as the name field in the frontmatter. |
| openjiuwen.02001128 | MAX_UPLOAD_SIZE_EXCEEDED | 400 | Maximum upload size exceeded. | The size of the file to be uploaded exceeds the system limit. | Please check the size of the uploaded file. |

## Agent-Referenced Skill Error Codes (module sub-code 0210)

| Full Error Code | Enum Name | HTTP Status | Default Message | Reason | Suggestion |
|------|------|------|------|------|------|
| openjiuwen.02101049 | SKILL_NUM_EXCEED_LIMIT | 400 | The number of skills exceeds the maximum limit. | The number of skills exceeds the maximum limit. | Reduce the number of skills and try again. |
| openjiuwen.02101050 | SKILL_NOT_EXIST | 404 | The skill does not exist. | The skill does not exist. | Ensure that the skill ID is correct and the skill exists. |
| openjiuwen.02101051 | SKILL_VERSION_INVALID | 400 | Invalid skill version. | The skill version is invalid or does not exist. | Ensure that the skill has the corresponding version enabled. |
| openjiuwen.02101052 | SKILL_ID_OR_VERSION_NOT_MATCH | 400 | Skill ID or version does not exist or does not match. | The specified skill ID or version does not exist or does not match the expected configuration. | Please ensure that the skill ID and version are correct and match the available skill configurations. |

## References

- Enum definition: `backend/studio-common/src/main/java/com/openjiuwen/studio/agent/common/enums/StudioError.java`
- Chinese messages: `backend/studio-common/src/main/resources/i18n/studio-messages_zh_CN.properties`
- English messages: `backend/studio-common/src/main/resources/i18n/studio-messages_en_US.properties`

> Note: The backend enum and i18n files are the single source of truth for the error codes and messages above. If the code changes, please synchronize this document.