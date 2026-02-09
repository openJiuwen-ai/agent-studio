# openjiuwen.agent_builder.tune.base

## class openjiuwen.agent_builder.tune.base.Case

```python
openjiuwen.agent_builder.tune.base.Case(inputs: Dict[str, Any], label: Dict[str, Any], tools: Optional[List[ToolInfo]] = None)
```

Defines a test case that includes input parameters, expected output, and optional tool information.
**Parameters:**

- **inputs** (Dict[str, Any]): The input parameters for the case.
- **label** (Dict[str, Any]): The expected output or label information used to verify correctness.
- **tools** (List[ToolInfo], optional): The list of tools (e.g., APIs, plugins) available to this case for multi-tool collaboration scenarios. Default: None.

**Examples:**

```python
>>> from openjiuwen.agent_builder.tune.base import Case
>>>
>>> # Build test cases
>>> case1 = Case(
...     inputs={"query": "Shen Zibin, courtesy name Maoren, style name Jixuan, also known as Maoxiu, a native of Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)"},
...     label={"output": "[Shen Zibin]"},
... )
>>> case2 = Case(
...     inputs={"query": "Pan Zhiheng (c. 1536—1621), courtesy name Jingsheng, sobriquets Luanshaosheng and Binghuasheng, from Shexian and Yansi, Anhui, later settled in Jinling (modern Nanjing, Jiangsu)"},
...     label={"output": "[Pan Zhiheng]"}
... )
```

## class openjiuwen.agent_builder.tune.base.EvaluatedCase

```python
openjiuwen.agent_builder.tune.base.EvaluatedCase(case: Case, answer: Dict[str, Any], score: float = 0.0, reason: str = "")
```

EvaluatedCase represents a test case after evaluation, including the original case, model output, evaluation score, and explanatory reason. It is suitable for recording and analyzing results in automated evaluation workflows.

**Parameters:**

- **case** (Case): The original test case, including inputs, label, tools, etc.
- **answer** (Dict[str, Any]): The model’s output to compare with the label.
- **score** (float): The evaluation score in [0, 1], where higher is better.
- **reason** (str): The reason for passing or failing, used for debugging and analysis.

Examples:

```python
>>> from openjiuwen.agent_builder.tune.base import EvaluatedCase
>>> from openjiuwen.agent_builder.tune.base import Case
>>> # Build a test case
>>> case1 = Case(
...     inputs={"query": "Shen Zibin, courtesy name Maoren, style name Jixuan, also known as Maoxiu, a native of Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)"},
...     label={"output": "[Shen Zibin]"},
... )
>>>
>>> evaluated_case = EvaluatedCase(
...     case=case1,
...     answer={"output": "[Shen Zibin, Maoren]"},
...     score=0.0,
...     reason="Answers do not match; the model output includes 'Maoren' in addition to the reference answer."
... )
```