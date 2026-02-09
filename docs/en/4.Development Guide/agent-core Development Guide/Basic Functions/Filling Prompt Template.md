Prompt templates often contain fillable placeholders, which can refer to tool information, examples, variables, and other content. openJiuwen provides a prompt template class `Template`, where `content` represents the template content and is required. Use double curly braces `{{...}}` to mark placeholders that need to be filled later; in practice, replace these placeholders with specific content to format and ultimately generate a complete prompt.

# Instantiating the Template class

The Template class supports the following three types of input for the `content` parameter: `str` (string), `List[Dict]` (list of dictionaries), and `List[BaseMessage]` (list of `BaseMessage`). Below are the instantiation methods for `content` of these three types.

- `str` type: Instantiate the Template class with `content` as a string.

  ```python
  from openjiuwen.core.utils.prompt.template.template import Template
  template = Template(content="You are a Q&A assistant proficient in the field of {{domain}}\nUser question: {{query}}")
  ```

- `List[Dict]` type: Instantiate the Template class with `content` as a list of dictionaries.

  ```python
  from openjiuwen.core.utils.prompt.template.template import Template
  template = Template(
      content=[
          {"role": "system", "content": "You are a Q&A assistant proficient in the field of {{domain}}"},
          {"role": "user", "content": "User question: {{query}}"}
      ]
  )
  ```

- `List[BaseMessage]` type: Instantiate the Template class with `content` as a list of BaseMessage.

  ```python
  from openjiuwen.core.utils.prompt.template.template import Template
  from openjiuwen.core.utils.llm.messages import SystemMessage, HumanMessage
  template = Template(
      content=[
          SystemMessage(role='system', content='You are a Q&A assistant proficient in the field of {{domain}}'),
          HumanMessage(role='user', content="User question: {{query}}")
      ]
  )
  ```

# Filling the Template

After instantiating the Template class, you can call the `.format` method to fill `content`. Example code:

```python
messages = template.format({"domain": "Mathematics", "query": "1+1=?"}).to_messages()
```
- The prompt template generated via the `str` type, after filling, results in:

  ```python
  [
      HumanMessage(role='user', content='You are a Q&A assistant proficient in the field of Mathematics\nUser question: 1+1=?', name=None)
  ]
  ```

- The prompt template generated via the `List[Dict]` type, after filling, results in:

  ```python
  [
      SystemMessage(role='system', content='You are a Q&A assistant proficient in the field of Mathematics', name=None),
      HumanMessage(role='user', content='User question: 1+1=?', name=None)
  ]
  ```

- The prompt template generated via the `List[BaseMessage]` type, after filling, results in:

  ```python
  [
      SystemMessage(role='system', content='You are a Q&A assistant proficient in the field of Mathematics', name=None),
      HumanMessage(role='user', content='User question: 1+1=?', name=None)
  ]
  ```

Placeholders marked with `{{...}}` will be correctly replaced with actual values, thereby generating complete input content.