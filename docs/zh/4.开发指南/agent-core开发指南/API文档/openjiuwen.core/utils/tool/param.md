# openjiuwen.core.utils.tool.param

## class openjiuwen.core.utils.tool.param.Param

Tool的参数配置类。

* **name**(str)：参数名称。
* **description**(str)：参数描述。说明该参数的含义和用途。
* **type**(str)：参数类型。取值可为`string`、`int`、`number`、`boolean`、`object`或`array`。
* **required**(bool)：参数是否为必填项。`True`表示必填，`False`表示可选。

**样例**：

```python
# 定义tool的参数类型
>>> from openjiuwen.core.utils.tool.param import Param
>>> 
>>> first_args = Param(name="a", description="第一个参数", type="int", required=True)
```
