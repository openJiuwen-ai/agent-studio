# openjiuwen.core.retrieval.utils.fusion

## function rrf_fusion

```python
rrf_fusion(results_list: List[List[RetrievalResult]], k: int = 60) -> List[RetrievalResult | SearchResult]
```

RRF（Reciprocal Rank Fusion）融合算法，用于融合多个检索结果列表。

**参数**：

* **results_list**(List[List[RetrievalResult]])：多个检索结果列表的列表。默认值：无。
* **k**(int)：RRF参数，默认值：60。

**返回**：

**List[RetrievalResult | SearchResult]**，返回融合后的检索结果列表，按RRF得分降序排序。

**说明**：

RRF算法通过以下公式计算融合得分：
```
score = sum(1.0 / (k + rank)) for each result list
```

其中rank是结果在每个列表中的排名（从1开始），k是RRF参数。

**样例**：

```python
>>> from openjiuwen.core.retrieval.utils.fusion import rrf_fusion
>>> from openjiuwen.core.retrieval.common.retrieval_result import RetrievalResult
>>> 
>>> # 假设有两个检索结果列表
>>> results1 = [
...     RetrievalResult(text="文档1", score=0.9),
...     RetrievalResult(text="文档2", score=0.8),
... ]
>>> results2 = [
...     RetrievalResult(text="文档2", score=0.85),
...     RetrievalResult(text="文档3", score=0.7),
... ]
>>> 
>>> # 融合结果
>>> fused = rrf_fusion([results1, results2], k=60)
>>> print(f"融合后结果数量: {len(fused)}")
融合后结果数量: 3
```

