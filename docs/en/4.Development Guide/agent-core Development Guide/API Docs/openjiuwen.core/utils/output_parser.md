# openjiuwen.core.utils.llm.output_parser.base.BaseOutputParser

## class openjiuwen.core.utils.llm.output_parser.base.BaseOutputParser

```python
openjiuwen.core.utils.llm.output_parser.base.BaseOutputParser()
```

BaseOutputParser is the base class for output parsers. The framework includes built-in parsers for JSON (JsonOutputParser) and Markdown (MarkdownOutputParser). To support additional output formats, inherit from BaseOutputParser and implement its abstract methods.

### async parse

```python
async parse(self, inputs: Union[str, AIMessage]) -> Any
```

Batch processing interface. Receives a single-shot input, converts it into the expected format, and returns the parsed data, typically one complete parsing result.

Parameters:
- inputs (Union[str, AIMessage]): The complete input for a single request.

Returns:
- Any: The parsed data, typically one complete parsing result.

### async stream_parse

```python
async stream_parse(self, streaming_inputs: Union[Iterator[str], Iterator[AIMessageChunk]]) -> Iterator[Any]
```

Streaming interface. Accepts an iterator as input, converts the content into the expected format, and returns an iterator that yields parsed data incrementally.

Parameters:
- streaming_inputs (Union[Iterator[str], Iterator[AIMessageChunk]]): The streaming input for a single request.

Returns:
- Iterator[Any]: An iterator where each yield returns a partial parsing result during streaming.

# openjiuwen.core.utils.llm.output_parser.json_output_parser.JsonOutputParser

## class openjiuwen.core.utils.llm.output_parser.json_output_parser.JsonOutputParser

```python
openjiuwen.core.utils.llm.output_parser.json_output_parser.JsonOutputParser(BaseOutputParser)
```

JsonOutputParser extracts and parses JSON data embedded in arbitrary text or LLM outputs.

### async parse

```python
async parse(self, llm_output: Union[str, AIMessage]) -> Any
```

Batch processing interface. Accepts LLM output as an AIMessage or str, extracts JSON data within it, and returns the parsed dictionary.

Parameters:
- llm_output (Union[str, AIMessage]): The complete input for a single request, either a model-returned string or an AIMessage object.

Returns:
- Any: The parsed JSON data (typically a dictionary). Returns None if parsing fails.

Example:
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
Output: {'item': 'apple', 'price': 1.5}
```

### async stream_parse

```python
async stream_parse(self, streaming_inputs: Iterator[Union[str, AIMessageChunk]]) -> Iterator[Optional[Dict[str, Any]]]
```

Streaming interface. Incrementally extracts and parses JSON data from the streaming input and returns parsed dictionaries in order.

Parameters:
- streaming_inputs (Iterator[Union[str, AIMessageChunk]]): The complete input for a single request, provided as an iterator of chunks (strings or AIMessageChunk objects). Each chunk comes from a streaming response; the method incrementally combines them into complete JSON data for parsing.

Returns:
- Iterator[Optional[Dict[str, Any]]]: An iterator where each iteration returns a parsed dictionary (if successful). It may yield None when parsing has not yet completed or fails.

Example:
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
Output: [{'data': 'value'}]
```

# openjiuwen.core.utils.llm.output_parser.markdown_output_parser.MarkdownOutputParser

## class openjiuwen.core.utils.llm.output_parser.markdown_output_parser.MarkdownOutputParser

```python
openjiuwen.core.utils.llm.output_parser.markdown_output_parser.MarkdownOutputParser(BaseOutputParser)
```

MarkdownOutputParser parses Markdown content embedded in arbitrary text or LLM outputs. It supports extracting and parsing various Markdown elements such as headers, code blocks, links, images, tables, and lists.

### async parse

```python
async parse(self, llm_output: Union[str, AIMessage]) -> Optional[MarkdownContent]
```

Batch processing interface. Accepts one-shot input and returns a single MarkdownContent result.

Parameters:
- llm_output (Union[str, AIMessage]): The LLM output as a string or AIMessage.

Returns:
- Optional[MarkdownContent]: The parsed MarkdownContent containing all extracted Markdown elements. Returns None if parsing fails.

Example:
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

Streaming interface. Accepts streaming input and yields MarkdownContent incrementally.

Parameters:
- streaming_inputs (Iterator[Union[str, AIMessageChunk]]): An iterator of LLM output chunks, either strings or AIMessageChunk objects.

Returns:
- Iterator[Optional[MarkdownContent]]: An iterator where each iteration yields a MarkdownContent object containing all Markdown elements parsed so far.

Example:
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