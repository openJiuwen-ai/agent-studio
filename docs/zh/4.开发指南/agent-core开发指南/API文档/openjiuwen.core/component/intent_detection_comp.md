# openjiuwen.core.component.intent_detection_comp

## class openjiuwen.core.component.intent_detection_comp.IntentDetectionCompConfig

意图识别组件的配置信息。

**参数**：

- **category_name_list**(List, 可选)：用户自定义的意图类别。默认值：`[]`，表示未配置意图类别。注意：意图识别组件默认添加默认意图，当任意一个用户定义的意图均匹配不上时，组件保证匹配默认意图作为兜底。
- **model**([ModelConfig](../common/configs/model_config.md#class-openjiuwencorecomponentcommonconfigsmodel_configmodelconfig))：大模型的配置信息。注意：未配置大模型、或配置大模型错误，组件将抛出异常。
- **user_prompt**(str, 可选)：用户自定义的提示词信息，该信息将作为片段填充到意图识别组件自带的提示词模板中，用于提示大模型更好地识别用户意图。默认值：`""`，表示未配置用户自定义的提示信息。可以不配置，该字段只会影响意图识别的效果。
- **example_content**(List[str], 可选)：用户自定义的示例，该信息将作为片段填充到意图识别组件自带的提示词模板中，用于提供示例、提示大模型更好地识别用户意图。默认值：`[]`，表示未配置示例。可以不配置，该字段只会影响意图识别的效果。
- ​**enable_history**(bool, 可选)​：表示调用大模型的输入信息中，是否使用对话历史，`True`表示使用对话历史，`False`表示不使用对话历史信息。默认值：`False`。
- **chat_history_max_turn**​(int, 可选)：表示选取对话历史的最大轮数（一轮具体指user-assistant一次对话）。取值范围：大于0的正整数，没有上限设置，达不到预设轮数的按照实际对话轮数取。默认值：3。注意：`enable_history=True`时该字段才生效，不足3轮时取实际的对话轮数。

## class openjiuwen.core.component.intent_detection_comp.IntentDetectionComponent

```python
class openjiuwen.core.component.intent_detection_comp.IntentDetectionComponent(component_config: Optional[IntentDetectionCompConfig] = None)
```

意图识别组件基于LLM对用户输入进行精准的意图解析与分类，并根据用户设置的下游分支路由规则，自动将任务流转至对应的工作流组件进行处理。

调用该组件时需要遵循以下约束：

- 输入：意图识别组件的输入需包括固定字段`query`，也支持输入自定义字段。
- 输出：意图识别组件的输出包括意图识别的结果，具体如下：
  
  - **classification_id**(int)：意图分类的序号，用户自定义意图从1开始，即`1`对应用户自定义的首个意图，后续意图类别依次递增；`0`对应默认意图，即所有用户自定义意图均匹配不上。
  - **category_name**(str)：识别后匹配到的用户意图的具体信息。
  - **reason**(str)：意图分类的理由。

**参数**：

- **component_config**([IntentDetectionCompConfig](#class-openjiuwencorecomponentintent_detection_compintentdetectioncompconfig), 可选)：意图识别组件的配置信息。

**异常**：

- ​**JiuWenBaseException**​：openJiuwen异常基类，详细信息和解决方法，请参见[StatusCode](../common/exception/status_code.md#class-openjiuwencorecommonexceptionstatus_codestatuscode)。

### add_branch

```python
add_branch(condition: Union[str, Callable[[], bool], Condition], target: Union[str, list[str]], branch_id: str = None)
```

意图识别组件通过`add_branch`方法添加路由到下游分支的规则。

**参数**：

- **condition**(Union[str, Callable[[], bool], Condition])：条件分支的表达式或条件对象。支持三种类型：
  - **str**：字符串表达式，表达式中需要包含意图识别组件在工作流中的id，`classification_id`对应意图识别组件的输出字段，`1`对应用户自定义的首个意图，后续依次递增。
  - **Callable[[], bool]**：可调用对象，返回布尔值表示条件是否满足。
  - **[Condition](./condition/condition.md)**：条件对象，实现了`Condition`接口的条件判断对象。具体实现包括`FuncCondition`、`ExpressionCondition`、`AlwaysTrue`等。
- **target**(Union[str, list[str]])：满足分支条件后，路由到下游组件id的集合。注意：目标下游组件id必须是工作流中已经添加的组件id，否则会抛出异常。
- **branch_id**(str, 可选)：分支路由的名称。默认值：`None`，表示未配置分支的名称。

**样例**：

对于创建成功的意图识别组件，添加路由到下游分支的规则。

```python
>>> import asyncio
>>> import os
>>> 
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.component.intent_detection_comp import IntentDetectionCompConfig, IntentDetectionComponent
>>> from openjiuwen.core.component.start_comp import Start
>>> from openjiuwen.core.component.end_comp import End
>>> from openjiuwen.core.runtime.workflow import WorkflowRuntime
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.workflow.base import Workflow
>>> 
>>> 
>>> os.environ['LLM_SSL_VERIFY']='false'
>>> 
>>> MODEL_PROVIDER = ""
>>> MODEL_NAME = ""
>>> API_BASE = ""
>>> API_KEY = ""
>>> 
>>> 
>>> async def demo_intent_dectection_component():
...     model_config = ModelConfig(
...         model_provider=MODEL_PROVIDER,
...         model_info=BaseModelInfo(
...         model=MODEL_NAME,
...         api_base=API_BASE,
...         api_key=API_KEY,
...         temperature=0.7,
...         top_p=0.9,
...         timeout=30  # 添加超时设置
...         ))
...     workflow = Workflow()
...     
...     config = IntentDetectionCompConfig(
...      category_name_list=["查询某地的景点", "查询某地天气"],
...      model=model_config,
...      user_prompt="请判断用户意图"
...     )
...     intent_component = IntentDetectionComponent(config)
...     
...     start_config = {
...          "inputs": [
...              {"id": "query", "required": True}
...          ]
...         }
...     
...     start_component = Start(start_config)
...     
...     intent_component.add_branch("${intent.classification_id} == 1", ["end"], "查询景点分支")
...     intent_component.add_branch("${intent.classification_id} == 2", ["end"], "查询天气分支")
...     intent_component.add_branch("${intent.classification_id} == 0", ["end"], "默认分支")
...     
...     # 通过`Workflow`的`add_workflow_comp`方法将意图识别组件对象添加到工作流中，定义组件名称为"intent"，输入参数中引用了开始组件的query字段的值。
...     workflow.set_start_comp("start", start_component, inputs_schema={"query": "${query}"})
...     workflow.set_end_comp("end", End(), inputs_schema={"output": "${intent}"})
...     workflow.add_workflow_comp(
...              "intent",
...              intent_component,
...              inputs_schema={"query": "${start.query}"},
...          )
...     workflow.add_connection("start", "intent")
...     workflow.add_connection("intent", "end")
...     result = await workflow.invoke({"query": "查询今天上海的天气", "conversation_id": "c123"}, WorkflowRuntime())
...     
...     print(f"{result.result.get('output', {}).get('output', result.result)}")
>>> 
>>> def main():
...     asyncio.run(demo_intent_dectection_component())
>>> 
>>> if __name__ == "__main__":
...    main()
>>> 
>>> 
>>> # 可能输出示例如下：
{
    "classification_id": 2,
    "reason": "用户问上海的天气怎么样，识别为查询天气的请求",
    "category_name": "查询某地天气"
}

>>> # 当用户输入为`"请推荐一家餐厅"`时
>>> result = await workflow.invoke({"query": "请推荐一家餐厅", "conversation_id": "c123"}, WorkflowRuntime())
>>> # 识别到意图既不是查天气的请求、也不是查景点的请求，则识别为默认意图，所以可能输出示例如下：
{
    "classification_id": 0,
    "reason": "用户请求未匹配任一意图，归类为默认意图",
    "category_name": "默认意图"
}
```
