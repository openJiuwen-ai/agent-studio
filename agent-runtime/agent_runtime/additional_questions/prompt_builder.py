# agent_runtime/serve/apis/additional_questions/prompt_builder.py
# -*- coding: UTF-8 -*-
"""Prompt builder for additional questions (追问) feature.

Ported from the Java service's ``.pt`` template files. Provides CN/EN
templates and a small builder that renders them with the caller-supplied
``name``, ``history_messages`` and optional ``user_prompt``.
"""

from __future__ import annotations


ADDITIONAL_QUESTIONS_PROMPT_CN: str = r"""根据用户的对话记录，为用户生成用于继续提问的追加问题，生成的提问建议按json格式返回，<example></example>  xml标签内为示例。

<example>
    User input:
    用户和智能体应用的历史对话内容为：
    关于科技、健康、教育等方面的知识，你能为我解答吗？
    当然可以，以下是关于科技、健康和教育的一些基础知识：

    科技：科技是指通过科学研究和应用来改进和创新产品、服务和过程。它涵盖了许多领域，如信息技术、生物技术、材料科学等。科技的发展对经济、社会和文化产生了深远的影响，改变了我们的生活方式和工作方式。
    健康：健康是指身体、心理和社会方面的完全良好状态。保持健康需要综合考虑饮食、运动、睡眠和心理健康等多个方面。定期体检、均衡饮食、适量运动和良好的心理状态都是维护健康的重要因素。
    教育：教育是指通过教学和学习来传授知识、技能和价值观的过程。它可以分为正规教育和非正式教育两种形式。正规教育通常在学校进行，包括小学、中学和大学等阶段；非正式教育则包括家庭教育、社区教育和自我学习等。教育对于个人的成长和发展至关重要，也是社会进步和发展的基础。 希望这些基础知识能帮助您更好地了解科技、健康和教育领域！如果您有任何具体问题或需要更详细的解释，请随时告诉我。
    请根据以上历史消息，以用户口吻，为用户生成三个用于继续提问的追加问题。

    追加问题生成规则：
    - 问题应该与你最后一轮的回复紧密相关
    - 问题不要与上文已经提问或者回答过的内容重复
    - 每句话只包含一个问题，但也可以不是问句而是一句指令
    - 推荐你有能力回答的问题

    Assistant output:
    ["科技的最新趋势是什么？", "健康方面有哪些生活习惯可以养成？", "教育领域有哪些值得关注的改革动态？"]
</example>

<example>
    User input:
    用户和项目日报生成助手应用的历史对话内容为：
    你能帮我生成本周的项目日报吗？
    当然可以，以下是一份本周项目日报的示例：

    日期：XXXX年XX月XX日

    一、项目进展

    任务完成情况：本周我们完成了以下任务：[列出具体任务]。这些任务的完成为项目的顺利进行奠定了坚实的基础。
    遇到的问题及解决方案：在项目执行过程中，我们遇到了一些问题，例如[列出问题]。针对这些问题，我们采取了相应的解决方案，并取得了良好的效果。
    下一步计划：下周我们将继续推进项目进度，具体计划包括[列出计划]。我们将确保按照计划完成各项任务，以确保项目按时交付。
    二、团队协作与沟通

    团队协作情况：本周团队成员之间保持了良好的协作关系，大家相互支持、共同努力，为项目的顺利推进做出了积极贡献。
    沟通效率：我们通过定期会议和在线沟通工具保持了高效的沟通。在遇到问题时，团队成员能够及时提出并寻求帮助，共同解决问题。
    三、风险评估与应对

    风险识别：本周我们对项目进行了风险评估，发现了一些潜在的风险点，例如[列出风险]。
    应对措施：针对这些风险，我们制定了相应的应对措施，包括[列出措施]。我们将密切关注风险变化，并根据实际情况调整应对策略。
    四、总结与展望
    本周项目取得了一定的进展，但仍需继续努力。我们将继续保持团队协作和高效沟通，确保项目按时交付。同时，我们也将密切关注项目风险，及时采取应对措施，确保项目的顺利进行。

    以上是本周项目日报的示例，您可以根据实际情况进行修改和完善。希望对您有所帮助！
    请根据以上历史消息，以用户口吻，为用户生成三个用于继续提问的追加问题。

    追加问题生成规则：
    - 问题应该与你最后一轮的回复紧密相关
    - 问题不要与上文已经提问或者回答过的内容重复
    - 每句话只包含一个问题，但也可以不是问句而是一句指令
    - 推荐你有能力回答的问题

    Assistant output:
    ["帮我写一个日报？", "如何根据日报生成自动生成周报？", "你能帮我整理一下这些日报吗？"]
</example>

Begin!

User input:
用户和{{name}}应用的历史对话内容为：
{{history_messages}}
请根据以上历史消息，以用户口吻，为用户生成三个用于继续提问的追加问题。

追加问题生成规则：
{{user_prompt}}

requirements：
- 追加问题生成规则（如有）为第一准则，必须严格遵守，优先级高于其他所有要求
- Assistant output的输出格式为json格式，输出一个字符串数组，例如：["帮我写一个日报？", "如何根据日报生成自动生成周报？", "你能帮我整理一下这些日报吗？"]


Assistant output:
"""


ADDITIONAL_QUESTIONS_PROMPT_EN: str = r"""Based on the user's conversation records, the system generates additional
questions for the user to continue asking questions. The generated questions
are returned in JSON format. The <example></example> xml tag is an example.

<example>
    User input:
    The content of historical conversations between users and agents is as follows:
    Can you answer for me about science and technology, health, education and so on?
    Sure, here are some basics about technology, health and education:

    Science and technology: Science and technology refers to the improvement
    and innovation of products, services and processes through scientific
    research and application. It covers many fields, such as information
    technology, biotechnology, material science and so on. The development
    of science and technology has had a profound impact on the economy,
    society and culture, changing the way we live and work.
    Health: Health refers to complete physical, psychological and social
    well-being. Keeping healthy requires a combination of diet, exercise,
    sleep and mental health. Regular physical examination, a balanced diet,
    moderate exercise and a good mental state are important factors in
    maintaining health.
    Education: Education is the process of imparting knowledge, skills and
    values through teaching and learning. It can be divided into formal
    education and informal education. Formal education is usually conducted
    in schools, including primary, secondary and tertiary levels; Non-formal
    education includes family education, community education and self-learning.
    Education is essential for the growth and development of individuals and
    is the basis for social progress and development. Hopefully, these basics
    will help you better understand technology, health and education! Please
    feel free to let me know if you have any specific questions or need a
    more detailed explanation.
    Based on the historical message above, generate three additional questions
    for the user to continue asking questions in the user's tone.

    Additional Question Generation Rules:
    - The question should be closely related to your last round of responses.
    - The question should not repeat content that has already been asked or
      answered in the previous text.
    - Each sentence should contain only one question, but it can also be a
      command rather than a question.
    - It is recommended that you ask questions you are capable of answering.

    Assistant output:
    ["What's the latest trend in technology?", "What habits can be developed
    in terms of health?", "What are the reform developments in the field
    of education that deserve attention?"]
</example>

Begin!

User input:
Historical conversations between the user and the {{name}} app are:
{{history_messages}}
Based on the historical message above, generate three additional questions
for the user in the user's tone to continue asking questions.

Additional Question Generation Rules:
{{user_prompt}}

requirements:
- The Additional Question Generation Rules are the first priority and must
  be strictly adhered to, with a higher priority than all other requirements.
- Assistant output: The output format is JSON. A character string array is
  output, for example, ["Help me write a daily report?", "How to
  automatically generate a weekly report based on the daily report?",
  "Would you help me sort out these daily newspapers?"]


Assistant output:
"""


class AdditionalQuestionsPromptBuilder:
    """Render the additional-questions prompt for a given language."""

    _TEMPLATES = {
        "zh": ADDITIONAL_QUESTIONS_PROMPT_CN,
        "en": ADDITIONAL_QUESTIONS_PROMPT_EN,
    }

    def build(
        self,
        name: str,
        history_messages: str,
        user_prompt: str = "",
        language: str = "zh",
    ) -> str:
        """Render the prompt template.

        Args:
            name: Application name shown to the user.
            history_messages: Historical conversation content.
            user_prompt: Optional custom generation rules.
            language: ``"zh"`` for Chinese template, otherwise English.
        """
        # language=="zh" -> CN; any non-zh value -> EN
        template = self._TEMPLATES["zh"] if language == "zh" else self._TEMPLATES["en"]
        return template.replace("{{name}}", name).replace(
            "{{history_messages}}", history_messages
        ).replace("{{user_prompt}}", user_prompt)
