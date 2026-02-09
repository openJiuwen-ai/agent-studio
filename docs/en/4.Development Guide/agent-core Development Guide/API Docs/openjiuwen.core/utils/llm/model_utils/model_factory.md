# class openjiuwen.core.utils.llm.model_utils.model_factory.ModelFactory

```python
openjiuwen.core.utils.llm.model_utils.model_factory.ModelFactory()
```

The ModelFactory class is used to load and manage multiple chat models and return the corresponding model instance based on the provided model identifier. This class follows the singleton pattern to ensure there is only one ModelFactory instance across the application.

## get_model

```python
get_model(model_provider: str, api_key: str, api_base: str, max_retrie: int=3, timeout: int=60) -> BaseModelClient
```

Obtain the corresponding model instance based on the model provider identifier.

**Parameters**:

- **model_provider** (str): The provider of the LLM service. Currently supports configuring `siliconflow` and `openai`.
- **api_key** (str): The API key for accessing the OpenAI LLM service, used for authentication and authorization.
- **api_base** (str): The URL of the LLM service endpoint.
- **max_retries** (int, optional): The maximum number of retry attempts when a request fails. Default: 3.
- **timeout** (int, optional): The timeout for a single LLM request in seconds. Default: 60 seconds.

**Returns**:

**BaseChatModel**, a model instance.

**Exceptions**:

- **ValueError**: No model implementation matched the given model_provider.

**Example**:

```python
>>> factory = ModelFactory()
>>> model = factory.get_model(
...     model_provider="xxxx",  
...     api_key="sk-xxx", 
...     api_base="your path to model service"
... )
>>> resp = model.invoke(
...     model_name="Qwen/Qwen3-8B",
...     messages="Hello!",
...     temperature=0.7, top_p=0.95
... )
>>> print(resp.content)
Hello, how can I help you?
```