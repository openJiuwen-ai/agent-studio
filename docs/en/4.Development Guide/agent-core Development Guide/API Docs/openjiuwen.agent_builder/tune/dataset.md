# openjiuwen.agent_builder.tune.dataset.case_loader

## class openjiuwen.agent_builder.tune.dataset.case_loader.CaseLoader

```python
openjiuwen.agent_builder.tune.dataset.case_loader.CaseLoader(cases: List[Case])
```

The CaseLoader class manages test cases, providing operations such as retrieval and shuffling for agent training, optimization, and related scenarios.

**Parameters:**

- **cases** (List[Case](base.md#class-openjiuwenagent_buildertunebasecase)): The list of test cases to load. Each `Case` should include input parameters (inputs), the expected output (label), and tools (optional).

**Examples:**

```python
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.dataset.case_loader import CaseLoader
>>>
>>> # Construct test cases
>>> case1 = Case(
...     inputs = {"query": "Shen Zibin, courtesy name Maoren, art name Jixuan, also known as Maoxiu, from Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)"},
...     label = {"output": "[Shen Zibin]"},
... )
>>> case2 = Case(
...     inputs={"query": "Pan Zhiheng (c. 1536—1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, a native of She County and Yansi, Anhui, who resided in Jinling (now Nanjing, Jiangsu)"},
...     label={"output": "[Pan Zhiheng]"}
... )
>>> case_loader = CaseLoader([case1, case2])
```

### shuffle

```python
shuffle(random_seed: int = 0)
```

Randomly shuffle the list of cases.

**Parameters:**

- **random_seed** (int, optional): Random seed used to control the shuffling result. Default: 0.

**Examples:**

```python
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.dataset.case_loader import CaseLoader
>>>
>>> # Construct test cases
>>> case1 = Case(
...     inputs = {"query": "Shen Zibin, courtesy name Maoren, art name Jixuan, also known as Maoxiu, from Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)"},
...     label = {"output": "[Shen Zibin]"},
... )
>>> case2 = Case(
...     inputs={"query": "Pan Zhiheng (c. 1536—1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, a native of She County and Yansi, Anhui, who resided in Jinling (now Nanjing, Jiangsu)"},
...     label={"output": "[Pan Zhiheng]"}
... )
>>> case_loader = CaseLoader([case1, case2])
>>> case_loader.shuffle()
>>> print(case_loader.get_cases())
[Case(inputs={'query': 'Shen Zibin, courtesy name Maoren, art name Jixuan, also known as Maoxiu, from Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)'}, label={'output': '[Shen Zibin]'}, tools=None, case_id='case_0'), Case(inputs={'query': 'Pan Zhiheng (c. 1536—1621) courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, a native of She County and Yansi, Anhui, who resided in Jinling (now Nanjing, Jiangsu)'}, label={'output': '[Pan Zhiheng]'}, tools=None, case_id='case_1')]
```

---

### size

```python
size() -> int
```

Return the total number of loaded cases.

**Returns:**

- **int:** The number of cases.

**Examples:**

```python
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.dataset.case_loader import CaseLoader
>>>
>>> # Construct test cases
>>> case1 = Case(
...     inputs = {"query": "Shen Zibin, courtesy name Maoren, art name Jixuan, also known as Maoxiu, from Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)"},
...     label = {"output": "[Shen Zibin]"},
... )
>>> case2 = Case(
...     inputs={"query": "Pan Zhiheng (c. 1536—1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, a native of She County and Yansi, Anhui, who resided in Jinling (now Nanjing, Jiangsu)"},
...     label={"output": "[Pan Zhiheng]"}
... )
>>> case_loader = CaseLoader([case1, case2])
>>> print(case_loader .size())
2
```

---

### get_cases

```python
get_cases() -> List[Case]
```

Return the list of cases.

**Returns:**

- **List[[Case](base.md#class-openjiuwenagent_buildertunebasecase)]**: All currently loaded cases.

**Examples:**

```python
>>> from openjiuwen.agent_builder.tune.base import Case
>>> from openjiuwen.agent_builder.tune.dataset.case_loader import CaseLoader
>>>
>>> # Construct test cases
>>> case1 = Case(
...     inputs = {"query": "Shen Zibin, courtesy name Maoren, art name Jixuan, also known as Maoxiu, from Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)"},
...     label = {"output": "[Shen Zibin]"},
... )
>>> case2 = Case(
...     inputs={"query": "Pan Zhiheng (c. 1536—1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, a native of She County and Yansi, Anhui, who resided in Jinling (now Nanjing, Jiangsu)"},
...     label={"output": "[Pan Zhiheng]"}
... )
>>> case_loader = CaseLoader([case1, case2])
>>> all_cases = case_loader.get_cases()
>>> for case in all_cases:
...     print(case.inputs)
{'query': 'Shen Zibin, courtesy name Maoren, art name Jixuan, also known as Maoxiu, from Changxi, Xiushui, Zhejiang (now Nanhui, Jiaxing)'}
{'query': 'Pan Zhiheng (c. 1536—1621), courtesy name Jingsheng, art names Luanxiaosheng and Binghuasheng, a native of She County and Yansi, Anhui, who resided in Jinling (now Nanjing, Jiangsu)'}
```