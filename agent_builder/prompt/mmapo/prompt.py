# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

ANSWER_CHECK_PROMPT_MM = """
        你是一位专业的答案校验专家，你的任务是评估给定的用户答案是否在含义上与标准答案一致，并根据你的评估结果给出相应的质量评分。

        **你需要严格遵循以下步骤和标准：**

        1. **理解问题：** 仔细阅读并理解以下带图片的问题：
        <question>
        {{question}}
        </question>
        
        2.  **分析标准答案：** 深入理解以下标准答案的含义和核心结论：
        <answer>
        {{answer}}
        </answer>

        3.  **解读用户答案：** 准确解读以下用户答案的含义和核心结论：
        <predict>
        {{predict}}
        </predict>

        4.  **进行含义一致性判断（忽略形式差异）：** 基于你对问题、图片、标准答案和用户答案的理解，判断用户答案的最终含义是否与标准答案一致。你需要考虑以下情况：
        - **数值的等价性：** 例如，1/2 和 0.5，百分数和分数/小数的转换等。
        - **表达方式的差异：** 例如，用不同的词语或句子结构表达了相同的概念或结论。
        - **单位的兼容性：** 在物理或计量问题中，单位可能不同但可以换算。
        **如果用户答案的最终含义与标准答案一致，即使表达形式不同，`result` 也应为 `true`。**

        5.  **评估回复质量并给出评分：** 根据你的一致性判断以及用户答案的推理过程、逻辑清晰度，给出一个0到10的评分：
        - **10分：** 用户答案的含义与标准答案完全一致，且推理过程完整、逻辑清晰。
        - **0分：** 用户答案的含义与标准答案完全不一致，且推理过程缺失或混乱。
        - **其他分数：** 根据用户答案的含义一致性程度、推理过程的完整性和逻辑清晰度，给出介于0到10之间的合理分数。

        6.  **输出JSON结果：** 根据你的判断和评分，以严格的JSON格式输出结果：

        ```json
        {{
            "result": true/false,
            "reason": "校验理由",
            "score": 0-10
        }}
        ```

        - 如果用户答案的含义与标准答案一致，`result` 为 `true`，`reason` 为 "用户答案的含义与标准答案一致。"。
        - 如果用户答案的含义与标准答案不一致，`result` 为 `false`，`reason` 为 "用户答案的含义与标准答案不一致，具体原因为[请在此处清晰、简洁地说明不一致的具体原因。]"。
        - `score` 字段则填写你评估的0-10分的分数。

        **请注意：** 在 `reason` 字段中，对于 `result` 为 `false` 的情况，务必清晰、简洁地说明用户答案与标准答案含义不一致的具体原因。
        """

ANSWER_CHECK_PROMPT_MM_BAOXIAN = """
        你是一位专业的答案校验专家，你的任务是评估给定的用户答案是否在含义上与标准答案一致，并根据你的评估结果给出相应的质量评分。

        **你需要严格遵循以下步骤和标准：**

        1. **理解问题：** 仔细阅读并理解以下带图片的问题：
        <question>
        {{question}}
        </question>
        
        2.  **分析标准答案：** 深入理解以下标准答案的含义和核心结论：
        <answer>
        {{answer}}
        </answer>

        3.  **解读用户答案：** 准确解读以下用户答案的含义和核心结论：
        <predict>
        {{predict}}
        </predict>

        4.  **进行含义一致性判断（忽略形式差异）：** 基于你对问题、图片、标准答案和用户答案的理解，判断用户答案的最终含义是否与标准答案一致。你需要考虑以下情况：
        - **数值的等价性：** 例如，1/2 和 0.5，百分数和分数/小数的转换等。
        - **表达方式的差异：** 例如，用不同的词语或句子结构表达了相同的概念或结论。
        - **单位的兼容性：** 在物理或计量问题中，单位可能不同但可以换算。
        **如果用户答案的最终含义与标准答案一致，即使表达形式不同，`result` 也应为 `true`。**

        5.  **评估回复质量并给出评分：** 根据你的一致性判断以及用户答案的推理过程、逻辑清晰度、最终结果，给出一个0到10的评分：
        # 0–10 分档说明（强调格式信号）
        - **10 分｜完全匹配**        
            * 内容：与标准答案字符级一致（归一化换行和 BOM 后）。
            * 格式：Markdown AST 完全一致（标题/段落/列表/表格/代码块/引用/内联标记均一致）。
            * 可读性&风险：渲染 1:1，无歧义。
        
        - **9 分｜微差但无结构影响**        
            * 内容：仅有不可见或等价差异（行尾空格、全角/半角空格、YAML Front-matter 的换行风格）。
            * 格式：**结构一致**；仅符号等价（`-` vs `*`）或表格对齐空格不同。
            * 可读性&风险：渲染一致或几乎一致。
        
        - **8 分｜轻微格式/内容小瑕疵，不破坏块结构**        
            * 格式：出现**1–2 处轻微格式偏差**，但不改变块结构（如在列表项末多了一个空行；软换行 `<br>` 与硬换行互换但段落仍独立）。
            * 内容：允许 1 处不影响理解的错别字/标点。
            * 关键信号：所有**段落/标题/表格块仍被正确识别**。
        
        - **7 分｜轻微结构差异**
            * 格式：**1–2 处轻微结构差异**，如某个二级标题写成了三级；列表缩进少一个空格导致某**个**子项与父项并列，但总体层级可恢复。
            * 内容：与标准答案一致或只有极小出入。
            * 关键信号：**段落基本正确**，不存在大段合并；表格形状正确。
        
        - **6 分｜中度结构错误（以格式为主）**
            * 格式：**2–3 处会影响阅读的结构问题**，例如：       
              * 多个应分段的条款被合并成一个段落；
              * 表格某行缺少管道导致该行渲染异常，但总体列数仍可推断；
              * 列表嵌套层级在局部错乱。
            * 内容：基本正确（关键信息未丢）。
            * 关键信号：需要读者**稍加还原**才能稳定阅读。
        
        - **5 分｜内容中错或缺 + 格式基本可用**        
            * 格式：块结构大体正确（标题/段落/表格形状 OK），仅有若干排版问题。
            * 内容：**1–2 处关键但可校正的错误**或遗漏（如金额千分位/小数点样式误用、一个日期格式错误、一个字段漏写）。
            * 关键信号：**不会因格式而误配字段**，但需要内容校对。
        
        - **4 分｜明显差距（格式与内容混合问题）**        
            * 格式：**3–5 处结构错误**：如表头分隔线缺失导致表头不被识别；多处条款未分段；列表层级大范围不准。
            * 内容：**多处非关键字段**错误或缺失（3–5 处），主体条款尚在。
            * 关键信号：渲染后阅读体验明显下降，需系统性人工修复。
        
        - **3 分｜主要内容缺陷或严重结构错位**        
            * 格式：结构错误已**影响信息对应关系**（表格列移位、编号混乱导致条款归属不明）。
            * 内容：**关键字段缺失或不实**（一方名称/金额/日期等丢失或错误），但能看出是该合同/表格。
            * 风险：高，容易误导流程。
        
        - **2 分｜语义失真**        
            * 格式：结构近乎崩溃（大段合并、表格基本不可识别、列表全部扁平化）。
            * 内容：大量关键信息遗漏/错配，语义不可托。
            * 风险：极高，不能用于业务。
        
        - **1 分｜接近不可用**        
            * 格式：几乎没有有效 Markdown（纯长段、乱码）。
            * 内容：仅剩零散可辨词。
            * 风险：极高，需要重新 OCR。
        
        - **0 分｜完全不匹配**        
            * 内容：与标准答案无关、空输出或纯乱码。
            * 格式：无 Markdown 结构。
            * 风险：最大。

        6.  **输出JSON结果：** 根据你的判断和评分，以严格的JSON格式输出结果：

        ```json
        {{
            "result": true/false,
            "reason": "校验理由",
            "score": 0-10
        }}
        ```

        - 如果用户答案的含义与标准答案一致，`result` 为 `true`，`reason` 为 "用户答案的含义与标准答案一致。"。
        - 如果用户答案的含义与标准答案不一致，`result` 为 `false`，`reason` 为 "用户答案的含义与标准答案不一致，具体原因为[请在此处清晰、简洁地说明不一致的具体原因。]"。
        - `score` 字段则填写你评估的0-10分的分数。

        **请注意：** 在 `reason` 字段中，对于 `result` 为 `false` 的情况，务必清晰、简洁地说明用户答案与标准答案含义不一致的具体原因。
        """

SCIENCEQA_INSTRUCTION = """
你是一位专业的图像分析和知识解答助手。你的任务是根据提供的图片、文本问题和文本选项进行解答。

## 输入:
- 图片: <image>
{{IMAGE_0}}
</image>
- 文本问题: {{question}}
- 文本选项: {{choices}}

## 工作流程:
1.  **解答问题**:
    1.1 仔细观察图片，结合文本问题和文本选项，运用你的知识和分析能力进行解答。
    1.2 详细记录你的解题思路和推理过程。
    1.3 从你的解题过程中，确定你认为的正确选项作为「你的答案」。

## 输出格式要求:
请输出你认为的正确选项对应的数字，如0，1，2，3等

请严格按照上述流程和格式要求，仅按照输出格式要求输出。

"""

SCIENCEQA_INSTRUCTION_PROMPTPILOT = """
你是一位专业的图像分析和知识解答助手。你的任务是根据提供的图片、文本问题和文本选项进行解答，并将解答结果与给定的答案进行对比，判断是否一致。

## 输入:
- 图片: <image>
{{IMAGE_0}}
</image>
- 文本问题: {{question}}
- 文本选项: {{choices}}（请以数字形式输出答案，如选项为['选项1', '选项2', '选项3']，则答案输出0/1/2）

## 工作流程:
1.  **解答问题**:
    1.1 仔细观察图片，结合文本问题和文本选项，运用你的知识和分析能力进行解答。（若任务涉及对图片中特定元素判断，如判断溶液浓度，可添加“观察图片中溶液的体积和蓝色粒子的数量，通过浓度 = 粒子数量 / 溶液体积的公式来判断浓度高低”等具体方法描述）
    1.2 详细记录你的解题思路和推理过程。
    1.3 从你的解题过程中，确定你认为的正确选项作为「你的答案」（请以数字形式输出答案，如选项为['选项1', '选项2', '选项3']，则答案输出0/1/2）。

## 输出格式要求:
请输出你认为的正确选项对应的数字，如0，1，2，3等。

请严格按照上述流程和格式要求，仅按照输出格式要求输出。
"""

META_PROMPT = """
    **Role Definition:**  
    You are a {role description} specializing in {area of expertise}.

    **Background & Knowledge Base:**  
    You are working within the following context:  
    {background information, such as motivations, previous attempts, known limitations, or environment-specific constraints}.  
    Use knowledge from {knowledge_sources} (e.g., {examples}) to ensure your response is grounded and relevant.

    **Task Description:**  
    Your objective is to accomplish the following task:  
    {precise task definition: what needs to be done, for what purpose, and what a successful result looks like}.  
    Focus on producing an output that directly addresses this objective.

    **Specific Requirements:**  
    - {Content standards, such as accuracy, professionalism, etc.}  
    - {Output format requirements, e.g., paragraphs, lists, code blocks}  
    - {Style or reference}  
    - {Other rules or process instructions}

    **Example:**  
    Here is a sample output that meets expectations:  
    {example content}
    """

TRANSFORMED_PROMPT = """
    You are an expert prompt engineer. Your task is to generate a concrete, executable prompt instance (a grounded prompt) based on the provided "meta-template" and "user instruction."

    【Objectives】  
    1. The grounded prompt must be highly executable, directly usable by large language models to significantly improve output quality;  
    2. Retain the structure and format of the meta-template;  
    3. Clearly fill in or revise vague or abstract parts of the meta-template to closely reflect the real intent expressed in the user instruction;  
    4. **Preserve all variables written in double curly braces**, such as {{QueryContent}}. These should not be deleted, replaced, or altered, and must be placed at appropriate positions in the final prompt based on contextual meaning;  
    5. Avoid vague or generic expressions; the language must be clear, specific, and cover core constraints or expectations;  
    6. Wrap the generated grounded prompt within <INS> and </INS> tags for easy extraction.

    【Meta-template】  
    **Role Definition:**  
    You are a {role description} specializing in {area of expertise}.

    **Background & Knowledge Base:**  
    You are working within the following context:  
    {background information, such as motivations, previous attempts, known limitations, or environment-specific constraints}.  
    Use knowledge from {knowledge_sources} (e.g., {examples}) to ensure your response is grounded and relevant.

    **Task Description:**  
    Your objective is to accomplish the following task:  
    {precise task definition: what needs to be done, for what purpose, and what a successful result looks like}.  
    Focus on producing an output that directly addresses this objective.

    **Specific Requirements:**  
    - {Content standards, such as accuracy, professionalism, etc.}  
    - {Output format requirements, e.g., paragraphs, lists, code blocks}  
    - {Style or reference}  
    - {Other rules or process instructions}

    **Example:**  
    Here is a sample output that meets expectations:  
    {example content}

    【User Instruction】
    <instruction>  
    {{instruction}}
    </instruction> 

    Please generate the grounded prompt accordingly, The content of the prompt should be in Chinese: 
    <INS>  
    (your grounded prompt in Chinese here)
    </INS>  
    """

PLACEHOLDER_RESTORE_TEMPLATE = """
作为提示词优化专家，你的任务是根据给定信息补全提示词中的占位符
原始提示词：
<original_prompt>
{{original_prompt}}
</original_prompt>>

修改后的提示词：
<revised_prompt>
{{revised_prompt}}
</revised_prompt>

原提示词的占位符全集为：
<all_placeholders>
{{all_placeholders}}
</all_placeholders>

经比较，修改后的提示词比原提示词缺少了以下占位符：
<missing_placeholders>
{{missing_placeholders}}
</missing_placeholders>

你的目标是：
1. 恢复所有缺失的占位符到修改后的提示词<revised_prompt>中，参考原提示词，将占位符添加到合适的位置，尽量避免添加在示例中
2. 占位符需要以括号的形式添加到提示词中，例如“{占位符名称}”
3. 除了占位符的必要修改外，不许修改提示词内容
4. 直接返回添加完占位符的提示词，不要添加思考过程或其他额外内容
"""
