# openjiuwen.core.component.condition.expression

## class openjiuwen.core.component.condition.expression.ExpressionCondition

```python
class openjiuwen.core.component.condition.expression.ExpressionCondition(expression: str)
```

An expression-based condition implementation that supports using string expressions for complex condition evaluation. It is suitable for scenarios that require combining multiple conditions or performing complex logical checks. It features a rich expression syntax, ideal for complex condition composition.

**Parameters:**

- **expression** (str): The condition expression string. The length of expression must be within [0, 5000]. The expression follows these rules:
  
  - Supported comparison types include: greater than, greater than or equal to, less than, less than or equal to, equal to, not equal to, contains, does not contain, empty, not empty. Equality also includes array length checks.
  - Supported data types include: string, number, integer, boolean, object, array.
  - For dynamic references, use placeholder syntax like ${start.query} to construct dynamic boolean expressions. Here, ${ and } are the placeholder delimiters, and start.query is the content that refers to an input field or variable.
  - For logical evaluations, use the following logical operators to build boolean expressions:

| Type | Description | Example |
| :---: | :---: | :---: |
| `&&, and, \|\|, or` | AND/OR connectors to join multiple boolean expressions (compound expressions; each expression must be wrapped in parentheses) | `(${start.query} == "test_query") && ("query" not in ${start.var})` |
| `==, !=` | String comparison: whether two strings are the same or different | `${start.query} == "test_query"` |
| `in, not_in, not in` | String comparison: whether one string is in another string or not | `"query" in ${start.var}` |
| `is_empty` | Determine whether a string is empty, has length 0, or is absent | `is_empty(${start.query})` |
| `is_not_empty` | Determine whether a string is not empty | `is_not_empty(${start.query})` |
| `length, len, >=, >, <=, <` | String length comparison | `length(${start.query}) >= 1` |


**Exceptions**:

- **JiuWenBaseException**: The base exception for openJiuwen. For detailed information and solutions, see [StatusCode](../../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode).

**Examples**:

```python
>>> # 1. Import required classes
>>> from openjiuwen.core.component.condition.expression import ExpressionCondition
>>> 
>>> # 2. Create ExpressionCondition objects
>>> # Example 1: String empty/non-empty checks
>>> condition1_1 = ExpressionCondition(expression="is_not_empty(${start.query})")
>>> condition1_2 = ExpressionCondition(expression="is_empty(${start.query})")
>>> 
>>> # Example 2: String equality/inequality
>>> condition2_1 = ExpressionCondition(expression="${start.query} != '1'")
>>> condition2_2 = ExpressionCondition(expression="${start.query} == '1'")
>>> 
>>> # Example 3: String length checks
>>> condition3_1 = ExpressionCondition(expression="length(${custom_component.p_str}) > 1")
>>> condition3_2 = ExpressionCondition(expression="length(${custom_component.p_str}) == 1")
>>> condition3_3 = ExpressionCondition(expression="length(${custom_component.p_str}) != 1")
>>> condition3_4 = ExpressionCondition(expression="length(${custom_component.p_str}) < 1")
>>> 
>>> # Example 4: Numeric comparisons
>>> condition4_1 = ExpressionCondition(expression="${custom_component.p_int} == 1")
>>> condition4_2 = ExpressionCondition(expression="${custom_component.p_int} > 1")
>>> condition4_3 = ExpressionCondition(expression="${custom_component.p_int} != 1")
>>> 
>>> # Example 5: Boolean true/false checks
>>> condition5_1 = ExpressionCondition(expression="${custom_component.p_true} == true")
>>> condition5_2 = ExpressionCondition(expression="${custom_component.p_true} == false")
>>> condition5_3 = ExpressionCondition(expression="${custom_component.p_true} != true")
>>> condition5_4 = ExpressionCondition(expression="${custom_component.p_true} != false")
>>> 
>>> # Example 6: Object contains/does not contain
>>> # Note: access object inner values using ${custom_component.p_obj['key']}
>>> condition6_1 = ExpressionCondition(expression="'a' in ${custom_component.p_obj}")
>>> condition6_2 = ExpressionCondition(expression="'a' not in ${custom_component.p_obj}")
>>> 
>>> # Example 7: Array contains/does not contain
>>> # Note: access array elements using ${custom_component.p_obj[index]}
>>> condition7_1 = ExpressionCondition(expression="'1' in ${custom_component.p_array}")
>>> 
>>> # Example 8: Multi-level nested checks
>>> condition8_1 = ExpressionCondition(expression="${start.p_multi_nested}['level1']['level2']['key3'] > 5")
>>> condition8_2 = ExpressionCondition(expression="(len(${start.p_complex}) > 1) && (${start.p_complex}[0]['subkey'] == 'subvalue')")
>>> condition8_3 = ExpressionCondition(expression="(${start.p_nested}['level1']['key1'] == 'value1') && ('key2' in ${start.p_nested}['level1'])")
>>> condition8_4 = ExpressionCondition(expression="(${start.p_int} > 1) && (${start.p_str} == '2') && (${start.p_array} not in ['3', '4']) && (length(${start.p_obj}) > 0)")
```