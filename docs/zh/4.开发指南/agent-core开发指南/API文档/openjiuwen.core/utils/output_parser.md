# openjiuwen.core.utils.llm.output_parser.base.BaseOutputParser

## class openjiuwen.core.utils.llm.output_parser.base.BaseOutputParser

```python
openjiuwen.core.utils.llm.output_parser.base.BaseOutputParser()
```

BaseOutputParser是输出解析器的基类，框架内部实现了JsonOutputParser和MarkdownOutputParser的解析，用户需要其他功能的输出解析，需要继承BaseOutputParser实现其抽象方法。

### async parse

```python
async parse(self, inputs: Union[str, AIMessage]) -> Any
```

批处理接口。接收一次性输入，将输入内容转换为预期格式，返回解析后的数据，通常是一次完整的解析结果。

**参数**：

- **inputs**(Union[str, AIMessage])：单次请求的完整输入。

**返回**：

**Any**，返回解析后的数据，通常是一次完整的解析结果。

### async stream_parse

```python
async stream_parse(self, streaming_inputs: Union[Iterator[str], Iterator[AIMessageChunk]]) -> Iterator[Any]
```

流式数据处理接口。接收迭代器形式的输入，将输入内容转换为预期格式，返回一个迭代器，逐步输出解析后的数据。

**参数**：

- **streaming_inputs**(Union[Iterator[str], Iterator[AIMessageChunk]])：单次请求的完整输入。

**返回**：

**Iterator[Any]**，返回一个迭代器，在流式解析中，每次调用 `yield` 都会返回一个部分解析结果。

# openjiuwen.core.utils.llm.output_parser.json_output_parser.JsonOutputParser

## class openjiuwen.core.utils.llm.output_parser.json_output_parser.JsonOutputParser

```python
openjiuwen.core.utils.llm.output_parser.json_output_parser.JsonOutputParser(BaseOutputParser)
```

JsonOutputParser解析任意字符和大模型输出结果中包含的Json数据。

### async parse

```python
async parse(self, llm_output: Union[str, AIMessage]) -> Any
```

批处理接口。接受 `AIMessage` 或 `str` 类型的 LLM 输出，提取其中的 JSON 数据并返回解析后的字典格式。

**参数**：

- **llm_output**(Union[str, AIMessage])：单次请求的完整输入，可以是模型返回的字符串或`AIMessage`对象。

**返回**：

**Any**，返回解析后的JSON数据（通常为字典类型），如果解析失败则返回`None`。

**样例**：

```python
>>> from openjiuwen.core.utils.llm.output_parser.json_output_parser import JsonOutputParser
>>> import asyncio
>>>                                       
>>> markdown_json = "Here is some info:\n```json\n{\"item\": \"apple\", \"price\": 1.5}\n```\nThanks!"
>>>                                           
>>> async def main():
...     parser = JsonOutputParser()
...     result = await parser.parse(markdown_json)
...     print(result)
... 
>>> if __name__ == "__main__":
...     asyncio.run(main())
... 
输出结果如下：{'item': 'apple', 'price': 1.5}
```

### async stream_parse

```python
async stream_parse(self, streaming_inputs: Iterator[Union[str, AIMessageChunk]]) -> Iterator[Optional[Dict[str, Any]]]
```

流式数据处理接口。该方法会从流式输入中逐步提取和解析 JSON 数据，并按顺序返回解析后的字典。

**参数**：

- **streaming_inputs**(Iterator[Union[str, AIMessageChunk]])：单次请求的完整输入，输入是一个迭代器，包含多个数据块，可以是字符串或`AIMessageChunk`对象，每个数据块是从流式响应中读取的部分内容，方法会逐步将它们合并为完整的 JSON 数据进行解析。

**返回**：

**Iterator[Optional[Dict[str, Any]]]**，返回一个迭代器，每次迭代返回一个解析后的字典对象（如果解析成功），如果解析失败则可能返回`None`。

**样例**：

```python
>>> import asyncio
>>>  
>>> from openjiuwen.core.utils.llm.output_parser.json_output_parser import JsonOutputParser
>>> 
>>> async def main():
...     parser = JsonOutputParser()
...     json_str = ["```json\n", "{\"data\": ", "\"value\"}\n", "```"]
...     parsed_objects = []
...     async for obj in parser.stream_parse(iter(json_str)):
...         parsed_objects.append(obj)
...     print(parsed_objects)
... 
>>> if __name__ == "__main__":
...     asyncio.run(main())
... 
输出结果如下：[{'data': 'value'}]
```

# openjiuwen.core.utils.llm.output_parser.markdown_output_parser.MarkdownOutputParser

## class openjiuwen.core.utils.llm.output_parser.markdown_output_parser.MarkdownOutputParser

```python
openjiuwen.core.utils.llm.output_parser.markdown_output_parser.MarkdownOutputParser(BaseOutputParser)
```

MarkdownOutputParser解析任意字符和大模型输出结果包含的Markdown信息。该类用于解析 Markdown 格式的 LLM 输出。支持提取并解析 Markdown 内容中的各种元素，例如标题、代码块、链接、图片、表格、列表等。

### async parse

```python
async parse(self, llm_output: Union[str, AIMessage]) -> Optional[MarkdownContent]
```

批处理接口。接收一次性输入信息，返回一次性MarkdownContent数据结果。

**参数**：

- **llm_output**(Union[str, AIMessage])：LLM的输出，可以是字符串或`AIMessage`对象。

**返回**：

**Optional[MarkdownContent]**，返回解析后的`MarkdownContent`对象，包含解析出的所有Markdown元素。如果解析失败，则返回 `None`。

**样例**：

```python
>>> import asyncio
>>> 
>>> from openjiuwen.core.utils.llm.output_parser.markdown_output_parser import MarkdownOutputParser
>>> 
>>> async def main():
...     parser = MarkdownOutputParser()
...     json_str = """##
... The data shows:
... - Item 1: Important finding
... - Item 2: Another insight
... 
... ![Chart](https://example.com/chart.png)"""
...     relust = await parser.parse(json_str)
...     print(relust)
... 
>>> if __name__ == "__main__":
...     asyncio.run(main())
MarkdownContent(raw_content='##\nThe data shows:\n- Item 1: Important finding\n- Item 2: Another insight\n\n![Chart](https://example.com/chart.png)', elements=[MarkdownElement(type='header', content={'level': '2', 'title': 'The data shows:'}, start_pos=0, end_pos=18, raw='##\nThe data shows:'), MarkdownElement(type='list', content={'list': '- Item 1: Important finding\n- Item 2: Another insight'}, start_pos=19, end_pos=73, raw='- Item 1: Important finding\n- Item 2: Another insight'), MarkdownElement(type='image', content={'alt': 'Chart', 'url': 'https://example.com/chart.png'}, start_pos=74, end_pos=113, raw='![Chart](https://example.com/chart.png)')], headers=[{'level': '2', 'title': 'The data shows:', 'raw': '##\nThe data shows:'}], code_blocks=[], links=[], images=[{'alt': 'Chart', 'url': 'https://example.com/chart.png', 'raw': '![Chart](https://example.com/chart.png)'}], tables=[], lists=['- Item 1: Important finding\n- Item 2: Another insight'])
```

### async stream_parse

```python
async stream_parse(self, streaming_inputs: Iterator[Union[str, AIMessageChunk]]) -> Iterator[Optional[MarkdownContent]]
```

流式数据处理接口。接收流式数据输入，返回迭代数据MarkdownContent结果。

**参数**：

- **streaming_inputs**(Iterator[Union[str, AIMessageChunk]])：LLM 输出的迭代器，可以是字符串块或`AIMessageChunk`对象。

**返回**：

**Iterator[Optional[MarkdownContent]]**，返回一个迭代器，每次迭代返回一个`MarkdownContent`对象，包含当前已解析的所有 Markdown 元素。

**样例**：

```python
>>> import asyncio
>>> from openjiuwen.core.utils.llm.output_parser.markdown_output_parser import MarkdownOutputParser
>>> 
>>> async def main():
...     parser = MarkdownOutputParser()
...     chunks = [
...         "# Title\n\n",
...         "This is a paragraph.\n\n",
...         "```python\n",
...         "print('hello')\n",
...         "```\n\n",
...         "[Link](https://example.com)"
...     ]
... 
...     parsed_objects = []
...     async for obj in parser.stream_parse(iter(chunks)):
...         parsed_objects.append(obj)
...     print(parsed_objects)
... 
>>> if __name__ == "__main__":
...     asyncio.run(main())
... 
[MarkdownContent(raw_content='# Title\n\n', elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title')], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[], links=[], images=[], tables=[], lists=[]), MarkdownContent(raw_content='# Title\n\nThis is a paragraph.\n\n', elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title')], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[], links=[], images=[], tables=[], lists=[]), MarkdownContent(raw_content='# Title\n\nThis is a paragraph.\n\n```python\n', elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title')], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[], links=[], images=[], tables=[], lists=[]), MarkdownContent(raw_content="# Title\n\nThis is a paragraph.\n\n```python\nprint('hello')\n", elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title')], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[], links=[], images=[], tables=[], lists=[]), MarkdownContent(raw_content="# Title\n\nThis is a paragraph.\n\n```python\nprint('hello')\n```\n\n", elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title'), MarkdownElement(type='code_block', content={'language': 'python', 'code': "print('hello')"}, start_pos=31, end_pos=59, raw="```python\nprint('hello')\n```")], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[{'language': 'python', 'code': "print('hello')", 'raw': "```python\nprint('hello')\n```"}], links=[], images=[], tables=[], lists=[]), MarkdownContent(raw_content="# Title\n\nThis is a paragraph.\n\n```python\nprint('hello')\n```\n\n[Link](https://example.com)", elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title'), MarkdownElement(type='code_block', content={'language': 'python', 'code': "print('hello')"}, start_pos=31, end_pos=59, raw="```python\nprint('hello')\n```"), MarkdownElement(type='link', content={'text': 'Link', 'url': 'https://example.com'}, start_pos=61, end_pos=88, raw='[Link](https://example.com)')], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[{'language': 'python', 'code': "print('hello')", 'raw': "```python\nprint('hello')\n```"}], links=[{'text': 'Link', 'url': 'https://example.com', 'raw': '[Link](https://example.com)'}], images=[], tables=[], lists=[]), MarkdownContent(raw_content="# Title\n\nThis is a paragraph.\n\n```python\nprint('hello')\n```\n\n[Link](https://example.com)", elements=[MarkdownElement(type='header', content={'level': '1', 'title': 'Title'}, start_pos=0, end_pos=7, raw='# Title'), MarkdownElement(type='code_block', content={'language': 'python', 'code': "print('hello')"}, start_pos=31, end_pos=59, raw="```python\nprint('hello')\n```"), MarkdownElement(type='link', content={'text': 'Link', 'url': 'https://example.com'}, start_pos=61, end_pos=88, raw='[Link](https://example.com)')], headers=[{'level': '1', 'title': 'Title', 'raw': '# Title'}], code_blocks=[{'language': 'python', 'code': "print('hello')", 'raw': "```python\nprint('hello')\n```"}], links=[{'text': 'Link', 'url': 'https://example.com', 'raw': '[Link](https://example.com)'}], images=[], tables=[], lists=[])]
```
