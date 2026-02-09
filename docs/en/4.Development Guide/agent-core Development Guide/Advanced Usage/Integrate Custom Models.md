Users can customize model integration. You first need to obtain the model request URL (api_base) and the authentication token (api_key). Model integration typically involves the following three main steps:

1. Create a model file: Create a custom model file under the `openjiuwen/core/utils/llm/model_library` directory.
2. Implement a custom model class: This usually includes handling model request parameters, sending model requests, and processing the returned result data.
3. Use the custom model class: Create a model instance and call the methods it provides.

Below, using the already supported vendor siliconflow as an example, we explain how to implement custom model integration.

## Create the file and configure environment variables

Create a `siliconflow.py` file under the `openjiuwen/core/utils/llm/model_library` directory.

## Implement the custom model class

Implement a custom subclass `Siliconflow` that inherits from the parent class `BaseModelClient`. Initialize parameters such as the LLM service auth token `api_key` and the LLM service URL `api_base`. Implement the parent class’s abstract methods _invoke, _ainvoke, _stream, _astream (using the implementation from RequestChatModel) to actually call the model API to obtain responses, and wrap results into different data types (e.g., sync calls, async calls, streaming calls) to meet different usage scenarios.

```python
from typing import List, Dict, Any, Iterator, AsyncIterator
from pydantic import BaseModel
from openjiuwen.core.utils.llm.base import BaseModelClient
from openjiuwen.core.utils.llm.messages import AIMessage
from openjiuwen.core.utils.llm.messages_chunk import AIMessageChunk
from openjiuwen.core.utils.llm.model_utils.default_model import RequestChatModel

class Siliconflow(BaseModel, BaseModelClient):
    _request_model: RequestChatModel = None

    def __init__(self,
                 api_key: str, api_base: str, max_retrie: int = 3, timeout: int = 60, **kwargs):
        super().__init__(api_key=api_key, api_base=api_base, max_retrie=max_retrie, timeout=timeout)
        self._request_model = RequestChatModel(api_key=api_key, api_base=api_base,
                                               max_retrie=max_retrie, timeout=timeout)
        self._should_close_session = True

    async def close(self):
        if hasattr(self, '_request_model') and self._request_model:
            if hasattr(self._request_model, 'close'):
                await self._request_model.close()
            self._request_model = None

    def model_provider(self) -> str:
        return "siliconflow"

    def _invoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: float = 0.1,
                top_p: float = 0.1, **kwargs: Any) -> AIMessage:
        return self._request_model._invoke(
            model_name=model_name, messages=messages, tools=tools,
            temperature=temperature, top_p=top_p, **kwargs)

    async def _ainvoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: float = 0.1,
                       top_p: float = 0.1, **kwargs: Any) -> AIMessage:
        return await self._request_model._ainvoke(
            model_name=model_name, messages=messages, tools=tools,
            temperature=temperature, top_p=top_p, **kwargs)

    def _stream(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: float = 0.1,
                top_p: float = 0.1, **kwargs: Any) -> Iterator[AIMessageChunk]:
        return self._request_model._stream(
            model_name=model_name, messages=messages, tools=tools,
            temperature=temperature, top_p=top_p, **kwargs)

    async def _astream(self, model_name:str, messages: List[Dict], tools: List[Dict] = None, temperature:float = 0.1,
               top_p:float = 0.1, **kwargs: Any) -> AsyncIterator[
        AIMessageChunk]:
        async for chunk in self._request_model._astream(
            model_name=model_name, messages=messages, tools=tools,
            temperature=temperature, top_p=top_p, **kwargs):
            yield chunk
```

RequestChatModel is an internally implemented HTTP-based model client. Its _invoke implementation follows these steps: handle model request parameters, send the model request, and process the response data. Users can follow this flow to implement their own. Example code:

```python
from typing import List, Dict, Any
from openjiuwen.core.utils.llm.messages import AIMessage, UsageMetadata

# Handle model request parameters
def _request_params(self, model_name: str, temperature: float, top_p: float, messages: List[Dict],
                    tools: List[Dict] = None, **kwargs: Any) -> Dict:
    params = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        **kwargs
    }

    if tools:
        params["tools"] = tools

    return params


# Handle model response data
def _parse_response(self, response_data: Dict) -> AIMessage:
    """parse response"""
    choice = response_data.get("choices", [{}])[0]
    message = choice.get("message", {})

    return AIMessage(
        content=message.get("content", ""),
        tool_calls=message.get("tool_calls", []),
        usage_metadata=UsageMetadata(
            model_name=self.model_name,
            finish_reason=choice.get("finish_reason", ""),
            total_latency=response_data.get('usage', {}).get('total_tokens', 0)
        )
    )


def _invoke(self, model_name: str, messages: List[Dict], tools: List[Dict] = None, temperature: float = 0.1,
            top_p: float = 0.1, **kwargs: Any) -> AIMessage:
    messages = self.sanitize_tool_calls(messages)
    params = self._request_params(model_name=model_name, temperature=temperature, top_p=top_p,
                                  messages=messages, tools=tools, **kwargs)
    # Send model request
    response = self.sync_client.post(
        verify=True,  # SSL verification is enabled by default; disable only in local testing scenarios
        url=self.api_base,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        },
        json=params,
        allow_redirects=False,
        timeout=self.timeout
    )
    response.raise_for_status()
    self.close_session()
    return self._parse_response(model_name, response.json())
```

## Use the custom model class

For details on using the custom model class, see [Integrate LLMs - Use models via ModelFactory](../Basic%20Functions/Connect%20to%20LLM.md#call-the-model). The `model_provider` is the class name of your custom implementation; in this example, it is siliconflow.