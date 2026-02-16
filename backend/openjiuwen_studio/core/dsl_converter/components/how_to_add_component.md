# How to Add a New Workflow Component - Detailed Guide

This document provides a detailed guide on how to add a new workflow component to the openJiuwen Studio platform. The guide is based on the actual implementation of the HTTP Request component from the recent commits and covers all necessary steps for both backend and frontend integration.

## Overview

Adding a new workflow component involves creating and modifying several files across both the backend and frontend. The process includes defining the component's data structures, implementing its execution logic, creating compilation and conversion logic, and integrating it into the visual workflow editor.

## Backend Implementation

### 1. Adding the component schema to dsl.py

#### 1.1 Add Component Type Enum
File: `backend/openjiuwen_studio/core/common/dsl.py`

Add a new component type to the `ComponentType` enum:
```python
class ComponentType(IntEnum):
    # ... existing types ...
    COMPONENT_TYPE_HTTP_REQUEST = 20,  # Add your component type here
```

#### 1.2 Define Component-Specific Enums
Still in `dsl.py`, define enums specific to your component:
```python
class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HttpAuthType(StrEnum):
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"


class HttpContentType(StrEnum):
    JSON = "application/json"
    FORM = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"
    TEXT = "text/plain"
    BINARY = "application/octet-stream"


class HttpResponseFormat(StrEnum):
    AUTO = "auto"
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"


class BackoffType(StrEnum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
```

#### 1.3 Register New Enums in Serialization
In the same file, add your new enums to the model_config's json_encoders:
```python
class BaseModel(PydanticBaseModel):
    model_config = {
        # ... existing encoders ...
        HttpMethod: lambda v: v.value,
        HttpAuthType: lambda v: v.value,
        HttpContentType: lambda v: v.value,
        HttpResponseFormat: lambda v: v.value,
        BackoffType: lambda v: v.value
    }
```

#### 1.4 Define Configuration Models
Create Pydantic models for your component's configuration:
```python
class HttpAuthConfig(BaseModel):
    auth_type: HttpAuthType = Field(HttpAuthType.NONE)
    username: Optional[str] = Field("")
    password: Optional[str] = Field("")
    token: Optional[str] = Field("")
    api_key: Optional[str] = Field("")
    api_key_location: Optional[str] = Field("header")  # header, query, body
    api_key_param_name: Optional[str] = Field("X-API-Key")


class HttpRequestBodyConfig(BaseModel):
    content_type: HttpContentType = Field(HttpContentType.JSON)
    content: Optional[Any] = Field(None)


class HttpRetryConfig(BaseModel):
    enabled: bool = Field(False)
    max_retries: int = Field(3)
    retry_on_status_codes: List[int] = Field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_delay_ms: int = Field(1000)
    backoff_type: BackoffType = Field(BackoffType.EXPONENTIAL)


class HttpRateLimitConfig(BaseModel):
    enabled: bool = Field(False)
    requests_per_unit: int = Field(10)
    unit: str = Field("minute")  # second, minute, hour


class HttpResponseHandlingConfig(BaseModel):
    response_format: HttpResponseFormat = Field(HttpResponseFormat.AUTO)
    success_status_codes: List[int] = Field(default_factory=lambda: [200, 201, 202, 204])
    failure_status_codes: List[int] = Field(default_factory=list)
    response_mode: str = Field("full")  # full, on-success, on-error
    data_property: Optional[str] = Field(None)  # e.g., "data.results"


class HttpAdvancedOptionsConfig(BaseModel):
    follow_redirects: bool = Field(True)
    ignore_ssl_issues: bool = Field(False)
    proxy_url: Optional[str] = Field(None)
    timeout: int = Field(60)


class HttpRequestParamConfig(BaseModel):
    key: str = Field("")
    value: Any = Field("")


class HttpRequestConfig(BaseModel):
    url: str = Field("")
    method: HttpMethod = Field(HttpMethod.GET)
    headers: List[HttpRequestParamConfig] = Field(default_factory=list)
    query_params: List[HttpRequestParamConfig] = Field(default_factory=list)
    body: Optional[HttpRequestBodyConfig] = Field(None)
    auth: HttpAuthConfig = Field(default_factory=HttpAuthConfig)
    response_handling: HttpResponseHandlingConfig = Field(default_factory=HttpResponseHandlingConfig)
    retry: HttpRetryConfig = Field(default_factory=HttpRetryConfig)
    rate_limit: HttpRateLimitConfig = Field(default_factory=HttpRateLimitConfig)
    advanced: HttpAdvancedOptionsConfig = Field(default_factory=HttpAdvancedOptionsConfig)
    exception_config: ExceptConfig = Field(default_factory=ExceptConfig)
```

### 2. Define Status Codes

#### 2.1 Add Component-Specific Status Codes
File: `backend/openjiuwen_studio/core/common/status_code.py`

Add status codes for your component's operations:
```python
class StatusCode(Enum):
    # ... existing codes ...
    HTTP_REQUEST_COMPONENT_INVOKE_ERROR = (BASE_CODE + 3007, "HTTP请求组件执行异常: {msg}",
                                           "HTTP request component invoke error: {msg}")
    HTTP_REQUEST_COMPONENT_CONVERT_FAILED = (BASE_CODE + 3045, "HTTP请求节点转换失败: {msg}",
                                             "HTTP request component convert failed: {msg}")
    HTTP_REQUEST_COMP_COMPILER_ERROR = (BASE_CODE + 3059, "HTTP请求组件编译失败: {msg}",
                                        "HTTP request component compiler failed: {msg}")
```

### 3. Implement Component Logic

#### 3.1 Create Component Implementation
File: `backend/openjiuwen_studio/core/executor/component/component_impl/http_request_comp.py`

Create the main component class that extends `WorkflowComponent`:
```python
from openjiuwen.core.workflow import WorkflowComponent
from openjiuwen_studio.core.common.dsl import HttpRequestConfig
from openjiuwen_studio.core.common.status_code import StatusCode

class HttpRequestComponent(WorkflowComponent):
    def __init__(self, node_id: str, conf: HttpRequestConfig) -> None:
        self.conf = conf
        self.node_id = node_id
        # Initialize other attributes

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        # Implement the main logic for your component
        try:
            # Your component's execution logic
            result = await self.execute_logic(inputs)
            return self.format_output(result)
        except Exception as e:
            # Handle errors appropriately
            return self.handle_error(e)
```

### 4. Create Compiler

#### 4.1 Create Component Compiler
File: `backend/openjiuwen_studio/core/executor/component/compile/http_request_comp_compiler.py`

Create a compiler class that extends `BaseCompCompiler`:
```python
from openjiuwen_studio.core.executor.component.compile.base_comp_compiler import BaseCompCompiler
from openjiuwen_studio.core.executor.component.component_impl.http_request_comp import HttpRequestComponent

class HttpRequestCompCompiler(BaseCompCompiler):
    def __init__(self, node_id: str, comp_config_dict: Dict[str, Any], workflow_connections: List[Connection]) -> None:
        super().__init__()
        self.comp_config_dict = comp_config_dict
        self.node_id = node_id
        self.workflow_connections = workflow_connections

    def compile(self) -> HttpRequestComponent:
        # Validate and convert config dict to HttpRequestConfig
        http_request_config = HttpRequestConfig.model_validate(self.comp_config_dict)
        
        # Create and return HTTP request component instance
        return HttpRequestComponent(self.node_id, http_request_config)
```

### 5. Create Component Converter

#### 5.1 Create Component Conversion Logic
File: `backend/openjiuwen_studio/core/manager/convertor/components/http_request.py`

Create conversion functions to transform frontend node data to DSL component:
```python
from openjiuwen_studio.schemas.node import Node
from openjiuwen_studio.core.common.dsl import Component, ComponentType, HttpRequestConfig

def http_request_convert(node: Node) -> Component:
    """Convert HTTP request node to DSL Component"""
    try:
        data = node.data
        inputs = data.inputs

        if inputs is None:
            raise TypeError("inputs is none")

        input_parameters = inputs.input_parameters
        if input_parameters is None:
            input_parameters = {}

        convert_inputs = input_params_convert(input_parameters)

        component = Component(
            id=node.id,
            type=ComponentType.COMPONENT_TYPE_HTTP_REQUEST,
            type_version="1.0.0",
            description="",
            inputs=convert_inputs,
            configs=_http_request_config_convert(node).model_dump(),
            name=data.title,
        )
        return component
    except Exception as e:
        raise RuntimeError(f"Failed to convert HTTP request node: {str(e)}") from e
```

#### 5.2 Register Converter in Main Converter
File: `backend/openjiuwen_studio/core/manager/convertor/component.py`

Import your converter and register it:
```python
from openjiuwen_studio.core.manager.convertor.components.http_request import http_request_convert

# In the component_convert function, add to the converters map:
converters: Dict[ComponentType, Callable[[Node], Component]] = {
    # ... existing converters ...
    ComponentType.COMPONENT_TYPE_HTTP_REQUEST: lambda n, s, sub: http_request_convert(n),
}

# Also add to the error code map:
error_code_map: Dict[int, int] = {
    # ... existing mappings ...
    ComponentType.COMPONENT_TYPE_HTTP_REQUEST: StatusCode.HTTP_REQUEST_COMPONENT_CONVERT_FAILED.code,
}
```

### 6. Update Workflow Executor

#### 6.1 Register Component Compilation Method
File: `backend/openjiuwen_studio/core/executor/workflow/workflow.py`

Import your compiler:
```python
from openjiuwen_studio.core.executor.component.compile.http_request_comp_compiler import HttpRequestCompCompiler
```

Register the compilation method in the `COMPONENT_COMPILE_MAP`:
```python
COMPONENT_COMPILE_MAP = {
    # ... existing mappings ...
    ComponentType.COMPONENT_TYPE_HTTP_REQUEST: '_compile_http_request_component',
}
```

Add the compilation method:
```python
async def _compile_http_request_component(self, comp: Component, workflow_dl: BaseFlow):
    """编译HTTP请求组件"""
    http_request_compiler = HttpRequestCompCompiler(comp.id, comp.configs, workflow_dl.connections)
    return http_request_compiler.compile()
```

### 7. Update Component Runner

#### 7.1 Allow Single Component Execution
File: `backend/openjiuwen_studio/core/executor/component/component_runner.py`

Add your component type to the `CAN_SINGLE_COMP_RUN` list:
```python
CAN_SINGLE_COMP_RUN = [
    # ... existing types ...
    ComponentType.COMPONENT_TYPE_HTTP_REQUEST,
]
```

#### 7.2 Add Component Type Display Name
In the same file, add your component type to the display name mapping:
```python
# In the get_component_display_name method:
m = {
    # ... existing mappings ...
    ComponentType.COMPONENT_TYPE_HTTP_REQUEST: "HTTP请求",
}
```

### 8. Update Node Schema

#### 8.1 Add Component-Specific Schema Definitions
File: `backend/openjiuwen_studio/schemas/node.py`

Add Pydantic models for your component's frontend representation:
```python
class HttpRequestParam(BaseModel):
    url: BaseValue = Field(..., alias="url")
    method: str = Field("GET", alias="method")
    headers: Optional[Dict[str, BaseValue]] = Field(None, alias="headers")
    query_params: Optional[Dict[str, BaseValue]] = Field(None, alias="queryParams")
    body: Optional[HttpBodyConfig] = Field(None, alias="body")
    # ... other fields

class Inputs(BaseModel):
    # ... existing fields ...
    http_request_param: Optional[HttpRequestParam] = Field(None, alias="httpRequestParam")
    method: Optional[BaseValue] = Field(None, alias="method")
```

## Frontend Implementation

### 1. Define Node Type Constant

#### 1.1 Add Node Type Enum Value
File: `frontend/packages/workflow-canvas/src/nodes/constants.ts`

Add your component type to the enum:
```typescript
export enum WorkflowNodeType {
  // ... existing types ...
  HttpRequest = '20',  // Use the same number as in the backend
}
```

### 2. Register Node in Node Panel

#### 2.1 Update Node List
File: `frontend/packages/workflow-canvas/src/components/node-panel/node-list.tsx`

Add your component to the type-name mapping:
```typescript
const nodeTypeKeyNames: Record<WorkflowNodeType, string> = {
  // ... existing mappings ...
  [WorkflowNodeType.HttpRequest]: 'HttpRequest',
}

// Add to i18n mapping:
const nodeTypeI18nKeys: Record<WorkflowNodeType, string] = {
  // ... existing mappings ...
  [WorkflowNodeType.HttpRequest]: 'workflowCanvas.node.HttpRequest',
}

// Add to category list:
const nodeCategories = {
  // ... existing categories ...
  components: {
    nameKey: 'workflowCanvas.category.components',
    nodes: [WorkflowNodeType.Questioner, WorkflowNodeType.TextEditor, WorkflowNodeType.HttpRequest],
  },
}
```

### 3. Create Node Implementation

#### 3.1 Create Node Registry
File: `frontend/packages/workflow-canvas/src/nodes/http-request/index.tsx`

Create the main node registry:
```typescript
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
          // Define initial input values
        },
        outputs: {
          // Define output schema
        },
        exceptionConfig: {
          // Define exception handling configuration
        },
      },
    }
  },
}
```

#### 3.2 Create Form Meta
File: `frontend/packages/workflow-canvas/src/nodes/http-request/form-meta.tsx`

Define the form metadata for your component:
```typescript
import { FormMeta, ValidateTrigger } from '@flowgram.ai/free-layout-editor'
import { 
  provideJsonSchemaOutputs,
  syncVariableTitle,
  autoRenameRefEffect,
  validateWhenVariableSync,
} from '../../form-materials'
import { FormHeader, FormContent, FormInput, FormOutput } from '../../form-components'
import { HttpRequestNodeData } from './types'
import { MethodSelector } from './components'

export const FormRender = () => {
  return (
    <>
      <FormHeader />
      <FormContent>
        <MethodSelector />
        <FormInput
          showAddButton={false}
          deleteable={false}
          nameEditable={false}
          useFieldSchema={true}
        />
        <FormOutput showAddButton={false} readonly={true} />
      </FormContent>
    </>
  )
}

export const formMeta: FormMeta<HttpRequestNodeData> = {
  render: () => <FormRender />,
  validateTrigger: ValidateTrigger.onChange,
  validate: async () => ({ errors: [], warnings: [] }),
  plugins: [],
  effect: {
    title: syncVariableTitle,
    outputs: provideJsonSchemaOutputs,
    'inputs.inputParameters.*': [...autoRenameRefEffect, ...validateWhenVariableSync({ scope: 'public' })],
    // Add form effects as needed
  },
}
```

#### 3.3 Define Types
File: `frontend/packages/workflow-canvas/src/nodes/http-request/types.tsx`

Define TypeScript interfaces for your component:
```typescript
export interface HttpRequestParam {
  url: any  // BaseValue type
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS'
  headers?: Record<string, any>  // key-value pairs
  queryParams?: Record<string, any>  // key-value pairs
  body?: HttpBodyConfig
  auth: HttpAuthenticationConfig
  response: HttpResponseConfig
  advanced: HttpAdvancedConfig
}

export interface HttpRequestNodeData {
  title: string
  inputs: {
    httpRequestParam: HttpRequestParam
    inputParameters?: Record<string, any>
  }
  outputs: {
    type: 'object'
    properties: {
      statusCode: { type: 'integer'; description: string }
      headers: { type: 'object'; description: string }
      body: { type: 'string'; description: string }
      url: { type: 'string'; description: string }
      ok: { type: 'boolean'; description: string }
    }
    required: string[]
  }
  exceptionConfig: {
    retryTimes: number
    timeoutSeconds: number
    processType: 'break' | 'return_content' | 'execute_exception_step'
    returnContent?: Record<string, any>
    executeStep?: {
      defaultStep: string
      errorStep: string
    }
  }
}
```

#### 3.4 Create UI Components
Create additional UI components in the `components/` subdirectory as needed for your component's configuration form.

### 4. Register Node in the System

#### 4.1 Import and Register Node
File: `frontend/packages/workflow-canvas/src/nodes/index.ts`

Import your node registry:
```typescript
import { HttpRequestNodeRegistry } from './http-request'
```

Add to the registries array:
```typescript
export const nodeRegistries: FlowNodeRegistry[] = [
  // ... existing registries ...
  HttpRequestNodeRegistry,
]
```

### 5. Add Localization

#### 5.1 Add English Translations
File: `frontend/src/locales/workflow/en-US/nodes.json`

Add translations for your component:
```json
{
  "httpRequest": {
    "titlePrefix": "HTTP Request",
    "description": "Make HTTP/HTTPS requests to external APIs with authentication, retry logic, and response handling.",
    "urlSection": {
      "title": "URL Configuration",
      "description": "Configure the request URL and HTTP method"
    },
    // Add other translation keys as needed
  }
}
```

#### 5.2 Add Chinese Translations
File: `frontend/src/locales/workflow/zh-CN/nodes.json`

Add Chinese translations:
```json
{
  "httpRequest": {
    "titlePrefix": "HTTP请求",
    "description": "向外部API发起HTTP/HTTPS请求，支持认证、重试逻辑和响应处理。",
    "urlSection": {
      "title": "URL配置",
      "description": "配置请求URL和HTTP方法"
    },
    // Add other translation keys as needed
  }
}
```

## Summary

To add a new workflow component, you need to:

1. **Backend**:
   - Add component type enum and data structures to dsl.py
   - Define status codes
   - Implement component logic
   - Create compiler
   - Create converter
   - Update workflow executor
   - Update component runner
   - Update node schema

2. **Frontend**:
   - Define node type constant
   - Register node in node panel
   - Create node implementation (registry, form meta, types, UI components)
   - Register node in the system
   - Add localization

Following this guide ensures that your new component integrates properly with both the backend execution engine and the frontend visual workflow editor.