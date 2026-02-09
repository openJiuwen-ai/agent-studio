# class openjiuwen.core.utils.llm.model_utils.model_factory.ModelFactory

```python
openjiuwen.core.utils.llm.model_utils.model_factory.ModelFactory()
```

`ModelFactory`类用于加载和管理多个聊天模型，并根据提供的模型标识符返回对应的模型实例。该类遵循单例模式，确保整个应用中只有一个`ModelFactory`实例。

## get_model

```python
get_model(model_provider: str, api_key: str, api_base: str, max_retrie: int=3, timeout: int=60) -> BaseModelClient
```

根据模型提供者标识符获取对应的模型实例。

**参数**：

- **model_provider**(str)：大模型服务的提供商，当前支持配置`siliconflow`、`openai`。
- ​**api_key**​(str)：访问OpenAI大模型服务接口的API密钥，用于身份验证和权限校验。
- ​**api_base**​(str)：大模型服务接口的URL。
- ​**max_retries**​(int, 可选)：表示接口调用失败时的最大重试次数。默认值：3。
- ​**timeout**(int, 可选)：表示单次调用大模型请求的超时时间。单位：秒。默认值：60秒。

**返回**：

**BaseChatModel**，模型实例。

**异常**：

- ​**ValueError**​：未找到与`model_provider`匹配的模型实现。

**样例**：

```python
>>> factory = ModelFactory()
>>> model = factory.get_model(
...     model_provider="xxxx",  
...     api_key="sk-xxx", 
...     api_base="your path to model service"
... )
>>> resp = model.invoke(
...     model_name="Qwen/Qwen3-8B",
...     messages="你好！",
...     temperature=0.7, top_p=0.95
... )
>>> print(resp.content)
你好，有什么可以帮助你的吗？
```
