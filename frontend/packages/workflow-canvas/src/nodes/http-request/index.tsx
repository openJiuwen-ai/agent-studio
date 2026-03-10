/**
 * Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
 * SPDX-License-Identifier: MIT
 */

import { customNanoid } from '../../utils/nanoid-custom'
import { WorkflowNodeType } from '../constants'
import { FlowNodeRegistry } from '../../typings'
import { Globe } from 'lucide-react'
import { formMeta } from './form-meta'
import { t } from '../../i18n'
import { generateNodeTitle } from '../../utils/workflow-node-utils'

export const HttpRequestNodeRegistry: FlowNodeRegistry = {
  type: WorkflowNodeType.HttpRequest,
  info: () => ({
    icon: <Globe size={16} className="text-blue-600" />,
    description: t('workflowCanvas.nodes.httpRequest.description'),
  }),
  meta: {
    defaultPorts: [{ type: 'output' }, { type: 'input' }],
    useDynamicPort: true,
    size: {
      width: 360,
      height: 280,
    },
    nodePanelVisible: true,
    singleComponentDebug: true,
  },
  formMeta,
  onAdd(context?) {
    const nodeId = `http_request_${customNanoid(5)}`
    const titlePrefix = t('workflowCanvas.nodes.httpRequest.titlePrefix')
    const title = generateNodeTitle(WorkflowNodeType.HttpRequest, context, titlePrefix)

    return {
      id: nodeId,
      type: WorkflowNodeType.HttpRequest,
      data: {
        title: title,
        inputs: {
          method: {
            type: 'constant',
            content: 'GET',
          },
          inputParameters: {
            url: {
              type: 'constant',
              content: 'https://api.example.com/endpoint',
              schema: {
                type: 'string',
              },
              extra: {
                index: 1,
              },
            },
            headers: {
              type: 'constant',
              content: {},
              schema: {
                type: 'object',
              },
              extra: {
                index: 2,
              },
            },
            query: {
              type: 'constant',
              content: {},
              schema: {
                type: 'object',
              },
              extra: {
                index: 3,
              },
            },
            body: {
              type: 'constant',
              content: null,
              schema: {
                type: 'object',
              },
              extra: {
                index: 4,
              },
            },
            auth: {
              type: 'constant',
              content: {
                type: 'none',
              },
              schema: {
                type: 'object',
                properties: {
                  type: {
                    type: 'string',
                    enum: ['none', 'basic', 'bearer', 'api_key'],
                  },
                  username: {
                    type: 'string',
                  },
                  password: {
                    type: 'string',
                  },
                  token: {
                    type: 'string',
                  },
                  api_key: {
                    type: 'string',
                  },
                  api_key_location: {
                    type: 'string',
                    enum: ['header', 'query', 'body'],
                  },
                  api_key_param_name: {
                    type: 'string',
                  },
                },
              },
              extra: {
                index: 5,
              },
            },
          },
          httpRequestParam: {
            url: {
              type: 'constant',
              content: 'https://api.example.com/endpoint',
              schema: {
                type: 'string',
              },
            },
            method: 'GET',
            headers: {},
            queryParams: {},
            body: {
              contentType: 'application/json',
              content: null,
            },
            auth: {
              authType: 'none',
              username: '',
              password: '',
              token: '',
              apiKey: '',
              apiKeyLocation: 'header',
              apiKeyParamName: 'X-API-Key',
            },
            response: {
              responseFormat: 'auto',
              successStatusCodes: [200, 201, 202, 204],
              failureStatusCodes: [],
              responseMode: 'full',
              dataProperty: null,
            },
            advanced: {
              followRedirects: true,
              ignoreSslIssues: false,
              proxyUrl: null,
              timeout: 60,
              retry: {
                enabled: false,
                maxRetries: 3,
                retryOnStatusCodes: [429, 500, 502, 503, 504],
                retryDelayMs: 1000,
                backoffType: 'exponential',
              },
              rateLimit: {
                enabled: false,
                requestsPerUnit: 10,
                unit: 'minute',
              },
            },
          },
        },
        outputs: {
          type: 'object',
          properties: {
            error_code: {
              type: 'integer',
              description: t('workflowCanvas.nodes.httpRequest.output.errorCode'),
              extra: {
                index: 1,
              },
            },
            error_msg: {
              type: 'string',
              description: t('workflowCanvas.nodes.httpRequest.output.errorMsg'),
              extra: {
                index: 2,
              },
            },
            data: {
              type: 'object',
              description: t('workflowCanvas.nodes.httpRequest.output.data'),
              extra: {
                index: 3,
              },
            },
          },
          required: ['error_code', 'error_msg', 'data'],
        },
        exceptionConfig: {
          retryTimes: 0,
          timeoutSeconds: 60,
          processType: 'break',
          executeStep: {
            defaultStep: '0',
            errorStep: '1',
          },
        },
      },
    }
  },
}
