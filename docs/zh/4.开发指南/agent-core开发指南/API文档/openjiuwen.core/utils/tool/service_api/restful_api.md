# openjiuwen.core.utils.tool.service_api.restful_api

## class openjiuwen.core.utils.tool.service_api.restful_api.RestfulApi

```python
RestfulApi(name: str, description: str, params: List[Param], path: str, headers: dict, method: str, response: List[Param])
```

`RestfulApi`类用于定义和管理RESTful风格的API接口信息，包括接口名称、描述、参数、路径、请求头、请求方法和响应信息等，便于对API接口进行标准化管理和调用。

**参数**：

* **name** (str)：API接口的名称。用于标识该API接口，具有唯一性。
* **description** (str)：API接口的描述信息。用于说明该API接口的功能和用途。
* **params** (List[[Param](../param.md#class-openjiuwencoreutilstoolparamparam)])：API接口的请求参数列表。每个参数为`Param`对象，包含参数的详细信息。
* **path** (str)：API接口的请求路径。即API接口的URL地址。
* **headers** (dict)：API接口的请求头信息。以字典形式存储，键为请求头名称，值为请求头内容。
* **method** (str)：API接口的请求方法。取值可为`GET`、`POST`。
* **response** (List[[Param](../param.md#class-openjiuwencoreutilstoolparamparam)])：API接口的响应参数列表。每个参数为Param对象，用于描述接口返回数据的结构。可为空，为空代表函数不需要返回值。

**样例**：

```python
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # 创建天气查询插件的RestfulApi实例
>>> weather_plugin = RestfulApi(
...     name="WeatherReporter",
...     description="天气查询插件",
...     params=[
...         Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
...         Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
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

该接口不支持使用。

**异常**：

* ​**JiuWenBaseException**​：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../../../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> from openjiuwen.core.common.exception.exception import JiuWenBaseException
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # 创建天气查询插件的RestfulApi实例
>>> weather_plugin = RestfulApi(
...     name="WeatherReporter",
...     description="天气查询插件",
...     params=[
...         Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
...         Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
...     ],
...     path="your weather search api url",
...     headers={},
...     method="GET",
...     response=[],
... )

>>> # 准备输入参数
>>> inputs = {
...     "location": "beijing",
...     "date": "2023-10-01"
... }
... 
>>> try:
>>>     result = weather_plugin.invoke(inputs=inputs)
>>>     print(f"调用成功，返回结果: {result}")
>>> except JiuWenBaseException as e:
>>>     print(f"调用失败，返回结果: {e.error_code} : {e.message}")
调用失败，返回结果: 182000: restful api only support ainvoke
```

### ainvoke

```python
async ainvoke(inputs: Input, **kwargs) -> Output
```

调用RESTful API接口的异步方法，用于发送请求并获取接口响应结果。

**参数**：

* **inputs**(Input)：API接口的输入参数对象，包含接口调用所需的具体参数值。
* **kwargs**：可变关键字参数，用于传递额外的请求配置或参数。

**返回**：

**Output**，接口调用的响应结果。成功时返回接口返回的数据；失败时返回包含错误信息的字典，包含以下键：

* **constant.ERR_CODE**：错误代码。
* **constant.ERR_MESSAGE**：错误描述信息。
* **constant.RESTFUL_DATA**：错误相关的附加数据。

**异常**：

该方法内部已处理各类异常，并将异常转换为包含错误信息的返回值，不对外抛出异常。可能的错误场景包括：

* **requests.exceptions.ReadTimeout**：请求读取超时。
* **requests.exceptions.Timeout**：请求超时。
* **requests.exceptions.ProxyError**：代理连接错误。
* ​**JiuWenBaseException**​：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../../../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

**样例**：

```python
>>> import asyncio
>>> from openjiuwen.core.utils.tool.service_api.restful_api import RestfulApi
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> # 创建天气查询插件的RestfulApi实例
>>> weather_plugin = RestfulApi(
...     name="WeatherReporter",
...     description="天气查询插件",
...     params=[
...         Param(name="location", description="天气查询的地点，必须为英文", type="string", required=True),
...         Param(name="date", description="天气查询的时间，格式为YYYY-MM-DD", type="string", required=True),
...     ],
...     path="your weather search api url",
...     headers={},
...     method="GET",
...     response=[],
... )

>>> # 准备输入参数
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
>>> print(f"调用成功，返回结果: {result}")
调用成功，返回结果: beijing 2023-10-01的天气晴朗
```

### get_tool_info

```python
get_tool_info() -> ToolInfo
```

获取工具信息，主要用于生成json schema供大模型识别调用。

**返回**：

**ToolInfo**，接口调用的响应结果，包括工具的名字、描述、参数信息等。

**样例**：

```python
>>> tool_info = weather_plugin.get_tool_info()
>>> print(f"调用成功，返回结果: {tool_info}")
调用成功，返回结果: type='function' function=Function(name='WeatherReporter', description='天气查询插件', parameters=Parameters(type='object', properties={'location': {'description': '天气查询的地点，必须为英文', 'type': 'string'}, 'required': ['location', 'date'], 'date': {'description': '天气查询的时间，格式为YYYY-MM-DD', 'type': 'string'}}, required=['location', 'date']))
```
