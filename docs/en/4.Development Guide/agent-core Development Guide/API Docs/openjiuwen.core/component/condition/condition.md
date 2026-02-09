# openjiuwen.core.component.condition.condition

## class openjiuwen.core.component.condition.condition.FuncCondition

```python
class openjiuwen.core.component.condition.condition.FuncCondition(func: Callable[[], bool])
```

A function-based condition implementation that uses a parameterless function as the condition logic. Suitable for scenarios where simple logic needs to be encapsulated. It is flexible and can wrap any zero-argument function.

**Parameters:**

- **func** (Callable[[], bool]): A parameterless function that returns a boolean as the condition result. The function may contain arbitrarily complex logic.

**Example:**

```python
>>> # 1. Import required classes
>>> import os
>>> 
>>> from openjiuwen.core.component.condition.condition import FuncCondition
>>> 
>>> # 2. Define a condition function
>>> def allow_zero():
...     # Arbitrarily complex logic can go here
...     return str(os.environ.get("ALLOW_ZERO", "false")).lower() == "true"
>>> 
>>> # 3. Create a FuncCondition object
>>> condition = FuncCondition(func=allow_zero)
```

## class openjiuwen.core.component.condition.condition.AlwaysTrue

A condition implementation that always evaluates to true. Useful for unconditional loops that must be manually interrupted. It is the simplest option, always true, and can serve as the preset condition for the default branch.

**Example:**

```python
>>> # 1. Import required classes
>>> from openjiuwen.core.component.condition.condition import AlwaysTrue
>>> 
>>> # 2. Create an AlwaysTrue object
>>> condition = AlwaysTrue()
```