# openjiuwen.core.retrieval.indexing.processor.chunker.tokenizer_chunker

## class openjiuwen.core.retrieval.indexing.processor.chunker.tokenizer_chunker.TokenizerChunker

Fixed size chunker based on tokenizer.

### __init__

```python
__init__(chunk_size: int, chunk_overlap: int, tokenizer: Any, **kwargs: Any)
```

Initialize tokenizer-based chunker.

**Parameters**:

* **chunk_size**(int): Chunk size (number of tokens). Default: None.
* **chunk_overlap**(int): Chunk overlap size (number of tokens). Default: None.
* **tokenizer**(Any): Tokenizer, must have encode and decode methods. Default: None.
* **kwargs**(Any): Variable arguments for passing additional configuration parameters.

### chunk_text

```python
chunk_text(text: str) -> List[str]
```

Chunk text.

**Parameters**:

* **text**(str): Text to be chunked. Default: None.

**Returns**:

**List[str]**, returns a list of chunked texts.

