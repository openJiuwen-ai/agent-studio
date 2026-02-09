# openjiuwen.core.utils.tool.service_api.restful_api

## class openjiuwen.core.utils.tool.service_api.restful_api.RestfulApi

```python
RestfulApi(name: str, description: str, params: List[Param], path: str, headers: dict, method: str, response: List[Param])
```

The RestfulApi class is used to define and manage RESTful-style API interface information, including the API name, description, parameters, path, request headers, HTTP method, and response schema. It facilitates standardized management and invocation of API interfaces.

**Parameters**:

- **name** (str): The name of the API. Used to uniquely identify the API.
- **description** (str): A description of the API. Explains the functionality and purpose of the API.
- **params** (List[Param]): The list of request parameters. Each parameter is a Param object containing detailed parameter information.
- **path** (str): The request path (URL) of the API.
- **headers** (dict): Request headers for the API, stored as a dictionary with header names as keys and their values as values.
- **method** (str): The HTTP method for the API. Valid values are GET and POST.
- **response** (List[Param]): The list of response parameters. Each is a Param object describing the structure of the returned data. Can be empty, which means the function does not need to return a value.

**Example**:

```python
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # Create a RestfulApi instance for a weather query plugin
>>> weather_plugin = RestfulApi(
...     name="WeatherReporter",
...     description="Weather query plugin",
...     params=[
...         Param(name="location", description="The location for the weather query; must be in English", type="string", required=True),
...         Param(name="date", description="The date for the weather query in YYYY-MM-DD format", type="string", required=True),
...     ],
...     path="your weather search api url",
...     headers={},
...     method="GET",
...     response=[],
... )
...
```

### invoke

```python
invoke(inputs: Input, **kwargs) -> Output
```

This interface is not supported.

**Exceptions**:

- **JiuWenBaseException**: Base exception for openJiuwen. For details and solutions, see StatusCode.

**Example**:

```python
>>> from openjiuwen.core.common.exception.exception import JiuWenBaseException
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # Create a RestfulApi instance for a weather query plugin
>>> weather_plugin = RestfulApi(
...     name="WeatherReporter",
...     description="Weather query plugin",
...     params=[
...         Param(name="location", description="The location for the weather query; must be in English", type="string", required=True),
...         Param(name="date", description="The date for the weather query in YYYY-MM-DD format", type="string", required=True),
...     ],
...     path="your weather search api url",
...     headers={},
...     method="GET",
...     response=[],
... )

>>> # Prepare input parameters
>>> inputs = {
...     "location": "beijing",
...     "date": "2023-10-01"
... }
... 
>>> try:
>>>     result = weather_plugin.invoke(inputs=inputs)
>>>     print(f"Call succeeded, result: {result}")
>>> except JiuWenBaseException as e:
>>>     print(f"Call failed, result: {e.error_code} : {e.message}")
Call failed, result: 182000: restful api only support ainvoke
```

### ainvoke

```python
async ainvoke(inputs: Input, **kwargs) -> Output
```

Asynchronously invokes the RESTful API to send the request and obtain the response.

**Parameters**:

- **inputs** (Input): The input parameter object containing the values required to call the API.
- **kwargs**: Additional keyword arguments for extra request configuration or parameters.

**Returns**:

Output, the response result of the API call. On success, returns the data from the API. On failure, returns a dictionary containing error information with the following keys:

- **constant.ERR_CODE**: The error code.
- **constant.ERR_MESSAGE**: The error message.
- **constant.RESTFUL_DATA**: Additional data related to the error.

**Exceptions**:

This method handles exceptions internally and converts them into error information in the return value. It does not raise exceptions to the caller. Possible errors include:

- **requests.exceptions.ReadTimeout**: Read timeout.
- **requests.exceptions.Timeout**: Request timeout.
- **requests.exceptions.ProxyError**: Proxy connection error.
- **JiuWenBaseException**: Base exception for openJiuwen. For details and solutions, see StatusCode.

**Example**:

```python
>>> import asyncio
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # Create a RestfulApi instance for a weather query plugin
>>> weather_plugin = RestfulApi(
...     name="WeatherReporter",
...     description="Weather query plugin",
...     params=[
...         Param(name="location", description="The location for the weather query; must be in English", type="string", required=True),
...         Param(name="date", description="The date for the weather query in YYYY-MM-DD format", type="string", required=True),
...     ],
...     path="your weather search api url",
...     headers={},
...     method="GET",
...     response=[],
... )

>>> # Prepare input parameters
>>> inputs = {
...     "location": "beijing",
...     "date": "2023-10-01"
... }
... 
>>> async def ainvoke_plugin():
...     global result
...     result = await weather_plugin.ainvoke(inputs=inputs)
>>> 
>>> asyncio.run(ainvoke_plugin())
>>> print(f"Call succeeded, result: {result}")
Call succeeded, result: The weather in beijing on 2023-10-01 is sunny
```

### get_tool_info

```python
get_tool_info() -> ToolInfo
```

Retrieves tool information, primarily used to generate JSON Schema for model tool-call recognition.

**Returns**:

**ToolInfo**, including the tool name, description, parameter schema, etc.

**Example**:

```python
>>> tool_info = weather_plugin.get_tool_info()
>>> print(f"Call succeeded, result: {tool_info}")
Call succeeded, result: type='function' function=Function(name='WeatherReporter', description='Weather query plugin', parameters=Parameters(type='object', properties={'location': {'description': 'The location for the weather query; must be in English', 'type': 'string'}, 'required': ['location', 'date'], 'date': {'description': 'The date for the weather query in YYYY-MM-DD format', 'type': 'string'}}, required=['location', 'date']))
```