import type { CodeExampleItem } from './components/PublishApiPanel'
import type { JsonSchema } from '@/types/jsonSchema'

/** API 发布 demo（与接口返回结构一致，后续由接口返回替换） */
export const DEMO_API_PUBLISH = {
  api_name: 'runtime.publish.demo.apiName',
  api_desc: 'runtime.publish.demo.apiDesc',
  method: 'POST',
  url: 'http://localhost:8090/query',
  code_example: [
  {
    example_name: ['Shell'],
    examples: [
      `curl -X POST "{{data.url}}" -H "Content-Type: application/json" -d "{\\"space_id\\": \\"{{data.body.space_id}}\\", \\"conversation_id\\": \\"{{data.body.conversation_id}}\\", \\"messages\\": [{\\"id\\": \\"{{data.body.messages.0.id}}\\", \\"role\\": \\"{{data.body.messages.0.role}}\\", \\"content\\": \\"{{data.body.messages.0.content}}\\"}]}"`,
    ],
    language: 'Shell',
    title: 'Curl Request',
  },
  {
    example_name: ['Python'],
    examples: [
      `import json
import sys
import requests

url = "{{data.url}}"
headers = {
    "Content-Type": "application/json"
}
payload = {
    "space_id": "{{data.body.space_id}}",
    "conversation_id": "{{data.body.conversation_id}}",
    "messages": [
        {
            "id": "{{data.body.messages.0.id}}",
            "role": "{{data.body.messages.0.role}}",
            "content": "{{data.body.messages.0.content}}"
        }
    ]
}

response = requests.post(url, headers=headers, json=payload, stream=True)
response.raise_for_status()

# Use UTF-8 output to avoid encoding errors caused by special characters
sys.stdout.reconfigure(encoding="utf-8")

for line in response.iter_lines(decode_unicode=True):
    if not line or not line.startswith("data:"):
        continue

    data_text = line[len("data:"):].strip()
    try:
        event = json.loads(data_text)
    except json.JSONDecodeError:
        continue

    if event.get("type") == "TEXT_MESSAGE_CONTENT":
        delta = event.get("delta", "")
        if delta:
            print(delta, end="", flush=True)

print()`,
    ],
    language: 'Python',
    title: 'Python Request',
  },
  {
    example_name: ['JavaScript'],
    examples: [
      `const url = "{{data.url}}";

const payload = {
  space_id: "{{data.body.space_id}}",
  conversation_id: "{{data.body.conversation_id}}",
  messages: [
    {
      id: "{{data.body.messages.0.id}}",
      role: "{{data.body.messages.0.role}}",
      content: "{{data.body.messages.0.content}}",
    },
  ],
};

const response = await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify(payload),
});

if (!response.ok) {
  throw new Error(\`HTTP \${response.status}: \${response.statusText}\`);
}

const reader = response.body?.getReader();
const decoder = new TextDecoder("utf-8");
if (!reader) {
  throw new Error("Response body is empty");
}

let buffer = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split(/\\r?\\n/);
  buffer = lines.pop() ?? "";

  for (const line of lines) {
    if (!line.startsWith("data:")) continue;

    const dataText = line.slice(5).trim();
    if (!dataText) continue;

    try {
      const event = JSON.parse(dataText);
      if (event.type === "TEXT_MESSAGE_CONTENT" && event.delta) {
        process.stdout.write(event.delta);
      }
    } catch {
      // ignore malformed json chunks
    }
  }
}

process.stdout.write("\\n");`,
    ],
    language: 'JavaScript',
    title: 'Fetch Request',
  },
] as CodeExampleItem[],
}

/** 请求配置 demo：Header / Query / Body（JSON Schema，与接口返回结构一致时可替换） */
export const DEMO_HEADER_PARAMS: JsonSchema = {
  type: 'object',
  properties: {},
}

export const DEMO_QUERY_PARAMS: JsonSchema = {
  type: 'object',
  properties: {},
}

export const DEMO_BODY_PARAMS: JsonSchema = {
  type: 'object',
  properties: {
    conversation_id: {
      type: 'string',
      description: 'runtime.publish.demo.body.conversationId.description',
      example: '1774249384621-4b8746a1ef003',
    },
    messages: {
      type: 'array',
      description: 'runtime.publish.demo.body.messages.description',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'runtime.publish.demo.body.messages.items.id.description', example: 'ZbN5xyc' },
          role: { type: 'string', description: 'runtime.publish.demo.body.messages.items.role.description', example: 'user' },
          content: { type: 'string', description: 'runtime.publish.demo.body.messages.items.content.description', example: 'runtime.publish.demo.body.messages.items.content.example' },
        },
      },
    },
    space_id: {
      type: 'string',
      description: 'runtime.publish.demo.body.spaceId.description',
      example: '95732486',
    },
  },
  required: ['conversation_id', 'messages'],
}

/** 返回参数说明 demo（JSON Schema object，支持嵌套，与接口返回结构一致时可替换） */
export const DEMO_RETURN_PARAMS: JsonSchema = {
  type: 'object',
  properties: {
    RUN_STARTED: {
      type: 'object',
      description: 'runtime.publish.demo.return.runStarted.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.runStarted.type.description', example: 'RUN_STARTED' },
        threadId: { type: 'string', description: 'runtime.publish.demo.return.runStarted.threadId.description', example: 'thread_001' },
        runId: { type: 'string', description: 'runtime.publish.demo.return.runStarted.runId.description', example: 'run_001' },
        parentRunId: { type: 'string', description: 'runtime.publish.demo.return.runStarted.parentRunId.description', example: 'run_000' },
        input: { type: 'object', description: 'runtime.publish.demo.return.runStarted.input.description', properties: {} },
      },
    },
    STEP_STARTED: {
      type: 'object',
      description: 'runtime.publish.demo.return.stepStarted.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.stepStarted.type.description', example: 'STEP_STARTED' },
        stepName: { type: 'string', description: 'runtime.publish.demo.return.stepStarted.stepName.description', example: 'knowledge_retrieve' },
      },
    },
    STEP_FINISHED: {
      type: 'object',
      description: 'runtime.publish.demo.return.stepFinished.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.stepFinished.type.description', example: 'STEP_FINISHED' },
        stepName: { type: 'string', description: 'runtime.publish.demo.return.stepFinished.stepName.description', example: 'knowledge_retrieve' },
      },
    },
    REASONING_MESSAGE_START: {
      type: 'object',
      description: 'runtime.publish.demo.return.reasoningMessageStart.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageStart.type.description', example: 'REASONING_MESSAGE_START' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageStart.messageId.description', example: 'reason-001' },
        role: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageStart.role.description', example: 'assistant' },
      },
    },
    REASONING_MESSAGE_CONTENT: {
      type: 'object',
      description: 'runtime.publish.demo.return.reasoningMessageContent.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageContent.type.description', example: 'REASONING_MESSAGE_CONTENT' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageContent.messageId.description', example: 'reason-001' },
        delta: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageContent.delta.description', example: 'runtime.publish.demo.return.reasoningMessageContent.delta.example' },
      },
    },
    REASONING_MESSAGE_END: {
      type: 'object',
      description: 'runtime.publish.demo.return.reasoningMessageEnd.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageEnd.type.description', example: 'REASONING_MESSAGE_END' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.reasoningMessageEnd.messageId.description', example: 'reason-001' },
      },
    },
    TEXT_MESSAGE_START: {
      type: 'object',
      description: 'runtime.publish.demo.return.textMessageStart.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.textMessageStart.type.description', example: 'TEXT_MESSAGE_START' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.textMessageStart.messageId.description', example: 'msg_123' },
        role: { type: 'string', description: 'runtime.publish.demo.return.textMessageStart.role.description', example: 'assistant' },
      },
    },
    TEXT_MESSAGE_CONTENT: {
      type: 'object',
      description: 'runtime.publish.demo.return.textMessageContent.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.textMessageContent.type.description', example: 'TEXT_MESSAGE_CONTENT' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.textMessageContent.messageId.description', example: 'msg_123' },
        delta: { type: 'string', description: 'runtime.publish.demo.return.textMessageContent.delta.description', example: 'runtime.publish.demo.return.textMessageContent.delta.example' },
      },
    },
    TEXT_MESSAGE_END: {
      type: 'object',
      description: 'runtime.publish.demo.return.textMessageEnd.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.textMessageEnd.type.description', example: 'TEXT_MESSAGE_END' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.textMessageEnd.messageId.description', example: 'msg_123' },
        content: { type: 'string', description: 'runtime.publish.demo.return.textMessageEnd.content.description', example: 'runtime.publish.demo.return.textMessageEnd.content.example' },
      },
    },
    TOOL_CALL_START: {
      type: 'object',
      description: 'runtime.publish.demo.return.toolCallStart.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.toolCallStart.type.description', example: 'TOOL_CALL_START' },
        toolCallId: { type: 'string', description: 'runtime.publish.demo.return.toolCallStart.toolCallId.description', example: 'call_456' },
        toolCallName: { type: 'string', description: 'runtime.publish.demo.return.toolCallStart.toolCallName.description', example: 'get_weather' },
        parentMessageId: { type: 'string', description: 'runtime.publish.demo.return.toolCallStart.parentMessageId.description', example: 'msg_123' },
      },
    },
    TOOL_CALL_ARGS: {
      type: 'object',
      description: 'runtime.publish.demo.return.toolCallArgs.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.toolCallArgs.type.description', example: 'TOOL_CALL_ARGS' },
        toolCallId: { type: 'string', description: 'runtime.publish.demo.return.toolCallArgs.toolCallId.description', example: 'call_456' },
        delta: { type: 'string', description: 'runtime.publish.demo.return.toolCallArgs.delta.description', example: 'runtime.publish.demo.return.toolCallArgs.delta.example' },
      },
    },
    TOOL_CALL_END: {
      type: 'object',
      description: 'runtime.publish.demo.return.toolCallEnd.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.toolCallEnd.type.description', example: 'TOOL_CALL_END' },
        toolCallId: { type: 'string', description: 'runtime.publish.demo.return.toolCallEnd.toolCallId.description', example: 'call_456' },
      },
    },
    TOOL_CALL_RESULT: {
      type: 'object',
      description: 'runtime.publish.demo.return.toolCallResult.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.toolCallResult.type.description', example: 'TOOL_CALL_RESULT' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.toolCallResult.messageId.description', example: 'msg_tool_456' },
        toolCallId: { type: 'string', description: 'runtime.publish.demo.return.toolCallResult.toolCallId.description', example: 'call_456' },
        content: { type: 'string', description: 'runtime.publish.demo.return.toolCallResult.content.description', example: 'runtime.publish.demo.return.toolCallResult.content.example' },
        role: { type: 'string', description: 'runtime.publish.demo.return.toolCallResult.role.description', example: 'tool' },
      },
    },
    ACTIVITY_SNAPSHOT: {
      type: 'object',
      description: 'runtime.publish.demo.return.activitySnapshot.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.activitySnapshot.type.description', example: 'ACTIVITY_SNAPSHOT' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.activitySnapshot.messageId.description', example: 'activity_001' },
        activityType: { type: 'string', description: 'runtime.publish.demo.return.activitySnapshot.activityType.description', example: 'RECOMMEND_QUESTION' },
        content: { type: 'object', description: 'runtime.publish.demo.return.activitySnapshot.content.description', properties: {} },
        replace: { type: 'boolean', description: 'runtime.publish.demo.return.activitySnapshot.replace.description', example: true },
      },
    },
    ACTIVITY_DELTA: {
      type: 'object',
      description: 'runtime.publish.demo.return.activityDelta.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.activityDelta.type.description', example: 'ACTIVITY_DELTA' },
        messageId: { type: 'string', description: 'runtime.publish.demo.return.activityDelta.messageId.description', example: 'act-001' },
        activityType: { type: 'string', description: 'runtime.publish.demo.return.activityDelta.activityType.description', example: 'PLAN' },
        patch: { type: 'array', description: 'runtime.publish.demo.return.activityDelta.patch.description', items: { type: 'object', properties: {} } },
      },
    },
    CUSTOM: {
      type: 'object',
      description: 'runtime.publish.demo.return.custom.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.custom.type.description', example: 'CUSTOM' },
        name: { type: 'string', description: 'runtime.publish.demo.return.custom.name.description', example: 'PING' },
        value: { type: 'object', description: 'runtime.publish.demo.return.custom.value.description', properties: {} },
      },
    },
    RUN_FINISHED: {
      type: 'object',
      description: 'runtime.publish.demo.return.runFinished.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.runFinished.type.description', example: 'RUN_FINISHED' },
        threadId: { type: 'string', description: 'runtime.publish.demo.return.runFinished.threadId.description', example: 'thread_001' },
        runId: { type: 'string', description: 'runtime.publish.demo.return.runFinished.runId.description', example: 'run_001' },
        result: { type: 'null', description: 'runtime.publish.demo.return.runFinished.result.description', example: null },
      },
    },
    RUN_ERROR: {
      type: 'object',
      description: 'runtime.publish.demo.return.runError.description',
      properties: {
        type: { type: 'string', description: 'runtime.publish.demo.return.runError.type.description', example: 'RUN_ERROR' },
        message: { type: 'string', description: 'runtime.publish.demo.return.runError.message.description', example: 'Model overloaded, please retry later' },
        code: { type: 'string', description: 'runtime.publish.demo.return.runError.code.description', example: '0101' },
      },
    },
  },
}

/** 返回参数整体说明 demo */
export const DEMO_RETURN_OVERALL_DESC = 'runtime.publish.demo.returnOverallDesc'
