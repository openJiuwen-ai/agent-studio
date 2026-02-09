# openjiuwen.core.component.condition.condition

## class openjiuwen.core.component.condition.condition.FuncCondition

```python
class openjiuwen.core.component.condition.condition.FuncCondition(func: Callable[[], bool])
```

基于函数的条件判断实现，将一个无参函数作为条件判断逻辑。适用于需要封装简单逻辑判断的场景。特点是灵活，可以封装任意无参函数。

**参数**：

* **func**(Callable[[], bool])：一个无参数的函数，返回布尔值作为条件判断结果。函数内部可以包含任意复杂的判断逻辑。

**样例**：

```python
>>> # 1. 导入必要的类
>>> import os
>>> 
>>> from openjiuwen.core.component.condition.condition import FuncCondition
>>> 
>>> # 2. 定义一个条件函数
>>> def allow_zero():
...     # 这里可以包含任意复杂的判断逻辑
...     return str(os.environ.get("ALLOW_ZERO", "false")).lower() == "true"
>>> 
>>> # 3. 创建FuncCondition对象
>>> condition = FuncCondition(func=allow_zero)
```

## class openjiuwen.core.component.condition.condition.AlwaysTrue

恒成立的条件判断实现。适用于无条件循环，需要手动中断的场景。特点是最简单，始终成立，可以作为`default`分支的预设条件。

**样例**：

```python
>>> # 1. 导入必要的类
>>> from openjiuwen.core.component.condition.condition import AlwaysTrue
>>> 
>>> # 2. 创建AlwaysTrue对象
>>> condition = AlwaysTrue()
```
