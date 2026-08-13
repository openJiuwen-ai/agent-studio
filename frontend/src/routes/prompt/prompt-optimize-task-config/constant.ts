import { cdnAssetUrl } from 'src/single-spa/assets-url';
import {
  IConfigConstants,
  PromptType,
  TaskType,
  VariableType,
} from '@interfaces/prompt/prompt-optimize-task.interface';

/**
 * 将图片的相对路径转为完整带域名的路由，供其他服务使用
 * @param uri
 */
function processImageUri(uri: string): string {
  let processedUri = cdnAssetUrl(uri);
  if (processedUri.startsWith('http' )) {
    // 带了完整协议域名的，直接返回
    return processedUri;
  } else if( processedUri.startsWith('//')){
    // 没有协议的，默认用https
    return `https:${processedUri}`;
  }else {
    // 没有带域名的，需要拼接域名,直接用服务的域名
    return `${window.location.origin}${processedUri}`;
  }
}

export const ConfigConstants: IConfigConstants = {
  zh_cn: {
    backgroundPromptPlaceholder:
      '输入背景知识如：\n' +
      '工资卡 / 薪资卡：公司用于发放工资的指定卡片，通常是借记卡。\n' +
      '房贷卡 / 车贷卡：专门用于偿还住房贷款或汽车贷款的扣款账户对应的卡片。重要提示：用户说“还房贷的卡”时，大概率指的是绑定了房贷扣款协议的借记卡，而不是信用卡。\n' +
      '缴费卡：专门用于缴纳水、电、煤气、学费等生活费用的卡。\n' +
      '购物卡 / 消费卡：用户可能将用于日常消费主力的信用卡或借记卡如此命名。\n' +
      '理财卡：通常指关联了理财、基金、贵金属等投资账户的借记卡（如某些银行的“金卡”、“财富卡”级别）。',
    scoringCriteriaPlaceholder:
      '输入评分标准如：\n' +
      '    "任务类型": "",\n' +
      '    "其他说明": "",\n' +
      '    "评价规则": \n' +
      '        "0分": "",\n' +
      '        "1分": ""\n' +
      '    \n' +
      '    "输出字段": ""\n',
    promptExample: [
      {
        title: '银行客服',
        value:
          '# 任务 你是一个智能银行客服助手，你需要根据用户提供的付款卡信息中关于卡号、卡类别、别名等信息，在付款卡列表中筛选满足要求的付款卡，输出付款卡在当前列表中的下标。 \n' +
          '- 卡类别示例：消费卡、借记卡、活期账户 - 别名示例：车贷卡、房贷卡、主卡 ' +
          '# 注意 - 卡号可能有多张，需要把所有符合条件的找出来作为输出； ' +
          '- 如果用户输入的是卡号数字，如完整卡号或者尾号，需要做精确匹配； ' +
          '- 如果用户输入的是卡片类别，如消费卡、借记卡、活期账户等，需要精确匹配卡列表中的类别、描述等，若未能成功匹配，输出空列表；' +
          '- 如果用户说的是默认卡，那么取出第一张卡的信息； ' +
          '- 如果用户说的是如"第一个"、"第一张"，则表明是付款卡列表中的对应卡； ' +
          '- 如果用户表达的意图时付款卡列表中的卡都不对，需要修改，则输出空列表； ' +
          '# 输出格式： 下面是一个输出JSON格式示例 若匹配到两张满足客户描述的卡，则输出： {"payCard"：["下标1"，"下标2"]} 若未能匹配到任何满足客户描述的卡，则输出： {"payCard":[]} 直接输出JSON内容，不要输出其他内容，如对问题的分析或者如"```json"等标识符。 ' +
          "## 示例 示例1： 用户输入: {'paycardInfo': '默认卡', 'paycardlist': '[卡的下标:0, 卡号:9999000000000000008, 卡描述:借记卡, 别名:储蓄卡, 地区:北京卡的下标:1, 卡号:9999000000000000009, 卡描述:消费卡, 别名:副卡, 地区:广州卡的下标:2, 卡号:9999000000000000008, 卡描述:信用卡, 别名:主卡, 地区:南京]'} 输出: {\"payCard\": [\"0\"]} # 后台查找出的付款卡列表 {{paycardlist}} # 用户提供的付款卡信息 {{paycardInfo}}",
        type: PromptType.TEXT,
        taskType: TaskType.OBJECTIVE,
        scoringCriteria:
          '    "任务类型": "字段信息抽取任务，用户输入包含付款卡信息和付款卡列表，模型需从输入中提取满足条件的付款卡下标并以结构化JSON格式输出。",\n' +
          '    "其他说明": "输出必须为合法JSON格式，payCard字段必须存在且为字符串数组。下标应为字符串形式，如\\"0\\"，而非数字。字段顺序不影响评分，但必须严格遵循JSON语法规范。",\n' +
          '    "评价规则": \n' +
          '        "0分": "存在以下任一情况：输出格式不合法（如非JSON、缺少引号或括号）；字段缺失（如未包含payCard键）；payCard字段值与标准答案语义不一致（如下标错误、遗漏或多余）；字段内容不符合任务要求（如匹配了非精确匹配的卡类别）。",\n' +
          '        "1分": "输出格式合法且字段完整，payCard字段内容与标准答案语义一致。允许表达差异，如下标顺序不同、空列表与[]等，但语义必须相同。"\n' +
          '    ,\n' +
          '    "输出字段": \n' +
          '        "payCard": "匹配到的付款卡在列表中的下标列表，为字符串数组。例如：[\\"0\\", \\"2\\"]"\n' +
          '    \n',
        backgroundPrompt:
          '输入背景知识如：\n' +
          '工资卡 / 薪资卡：公司用于发放工资的指定卡片，通常是借记卡。\n' +
          '房贷卡 / 车贷卡：专门用于偿还住房贷款或汽车贷款的扣款账户对应的卡片。重要提示：用户说“还房贷的卡”时，大概率指的是绑定了房贷扣款协议的借记卡，而不是信用卡。\n' +
          '缴费卡：专门用于缴纳水、电、煤气、学费等生活费用的卡。\n' +
          '购物卡 / 消费卡：用户可能将用于日常消费主力的信用卡或借记卡如此命名。\n' +
          '理财卡：通常指关联了理财、基金、贵金属等投资账户的借记卡（如某些银行的“金卡”、“财富卡”级别）。',
        useCases: [
          [
            {
              name: 'paycardlist',
              type: VariableType.TEXT,
              content:
                '[卡的下标:0, 卡号:9999000000000000001, 卡描述:消费卡, 别名:工资卡, 地区:杭州卡的下标:1, 卡号:9999000000000000002, 卡描述:活期账户, 别名:工资卡, 地区:北京]',
            },
            {
              name: 'paycardInfo',
              type: VariableType.TEXT,
              content: '工资卡',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"payCard": ["0", "1"]}',
            },
          ],
          [
            {
              name: 'paycardlist',
              type: VariableType.TEXT,
              content:
                '[卡的下标:0, 卡号:9999000000000000003, 卡描述:消费卡, 别名:工资卡, 地区:成都卡的下标:1, 卡号:9999000000000000004, 卡描述:活期账户, 别名:房贷卡, 地区:杭州]',
            },
            {
              name: 'paycardInfo',
              type: VariableType.TEXT,
              content: '房贷卡',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"payCard": ["1"]}',
            },
          ],
          [
            {
              name: 'paycardlist',
              type: VariableType.TEXT,
              content: '[]',
            },
            {
              name: 'paycardInfo',
              type: VariableType.TEXT,
              content: '借记卡',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"payCard": []}',
            },
          ],
          [
            {
              name: 'paycardlist',
              type: VariableType.TEXT,
              content:
                '[卡的下标:0, 卡号:9999000000000000005, 卡描述:消费卡, 别名:工资卡, 地区:广州卡的下标:1, 卡号:9999000000000000005, 卡描述:活期账户, 别名:房贷卡, 地区:深圳]',
            },
            {
              name: 'paycardInfo',
              type: VariableType.TEXT,
              content: '借记卡',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"payCard": []}',
            },
          ],
          [
            {
              name: 'paycardlist',
              type: VariableType.TEXT,
              content:
                '[卡的下标:0, 卡号:9999000000000000005, 卡描述:消费卡, 别名:工资卡, 地区:广州卡的下标:1, 卡号:9999000000000000005, 卡描述:活期账户, 别名:房贷卡, 地区:深圳]',
            },
            {
              name: 'paycardInfo',
              type: VariableType.TEXT,
              content: '默认卡',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"payCard": ["0"]}',
            },
          ],
          [
            {
              name: 'paycardlist',
              type: VariableType.TEXT,
              content:
                '[卡的下标:0, 卡号:9999000000000000006, 卡描述:消费卡, 别名:工资卡, 地区:深圳卡的下标:1, 卡号:9999000000000000007, 卡描述:活期账户, 别名:房贷卡, 地区:南京]',
            },
            {
              name: 'paycardInfo',
              type: VariableType.TEXT,
              content: '消费卡',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"payCard": ["0"]}',
            },
          ],
        ],
      },
      {
        title: '知识解答助手',
        value:
          '你是一位专业的图像分析和知识解答助手。\n' +
          '你的任务是根据提供的图片、文本问题和文本选项进行解答。\n' +
          '## 输入:\n ' +
          '- 图片: {{IMAGE_0}} \n' +
          '- 文本问题: {{question}} \n' +
          '- 文本选项: {{choices}} \n' +
          '## 工作流程: \n' +
          '1. **解答问题**: \n' +
          '1.1 仔细观察图片，结合文本问题和文本选项，运用你的知识和分析能力进行解答。\n' +
          '1.2 详细记录你的解题思路和推理过程。\n' +
          '1.3 从你的解题过程中，确定你认为的正确选项作为「你的答案」。\n' +
          '## 输出格式要求: 请输出你认为的正确选项对应的数字，如0，1，2，3等 请严格按照上述流程和格式要求，仅按照输出格式要求输出。\n',
        type: PromptType.MULTI,
        taskType: TaskType.SUBJECTIVE,
        scoringCriteria: '允许表达差异，但语义必须相同',
        useCases: [
          [
            {
              name: 'IMAGE_0',
              type: VariableType.IMAGE,
              content: processImageUri(
                'assets/prompt/optimize-example/example-3.png',
              ),
            },
            {
              name: 'question',
              type: VariableType.TEXT,
              content: '以下哪个州最靠北？',
            },
            {
              name: 'choices',
              type: VariableType.TEXT,
              content: "['West Virginia', 'Louisiana', 'Arizona', 'Oklahoma']",
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '0',
            },
          ],
          [
            {
              name: 'IMAGE_0',
              type: VariableType.IMAGE,
              content: processImageUri(
                'assets/prompt/optimize-example/example-2.png',
              ),
            },
            {
              name: 'question',
              type: VariableType.TEXT,
              content: 'Tom和Justin的实验最能回答的问题是什么？',
            },
            {
              name: 'choices',
              type: VariableType.TEXT,
              content:
                "['乒乓球从30°角发射后，比从45°角发射后，会更早停止在地面上滚动吗？', '乒乓球从30°角发射时，比从45°角发射时，能飞得更远吗？']",
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '1',
            },
          ],
          [
            {
              name: 'IMAGE_0',
              type: VariableType.IMAGE,
              content: processImageUri(
                'assets/prompt/optimize-example/example-1.png',
              ),
            },
            {
              name: 'question',
              type: VariableType.TEXT,
              content: 'Kathleen 和 Bryant 的实验最能回答的问题是什么？',
            },
            {
              name: 'choices',
              type: VariableType.TEXT,
              content:
                "['Kathleen的滑雪板在有蜡层时，还是没有蜡层时，滑下山坡所需的时间更短？', 'Kathleen的滑雪板在表面有一层薄蜡时，还是有一层厚蜡时，滑下山坡所需的时间更短？']",
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '0',
            },
          ],
        ],
      },
    ] as const,
  },
  en_us: {
    backgroundPromptPlaceholder:
      'Enter the background:\n' +
      "Direct deposit account: usually a savings account that someone's salary is paid into.\n" +
      'Mortgage/Car loan account: an account dedicated to repaying a housing or car loan. Note: When a user mentions "the account used to pay the mortgage", it probably means a savings or checking account used to pay a mortgage.\n' +
      'Payment card: used to pay for utilities such as water, electricity, and gas, or to pay school tuition.\n' +
      'Shopping card: a credit or debit card used for daily expenses.\n' +
      'Wealth management card: a debit card associated with investments, such as equities or precious metals, often issued by wealth management organizations to their investors.\n',
    scoringCriteriaPlaceholder:
      'Enter scoring criteria:\n' +
      ' "Task Type":"",\n' +
      ' "Remarks":"",\n' +
      ' "Scoring Rules":\n' +
      '  "0 points": "",\n' +
      '  "1 point": ""\n' +
      ' "Output":""\n',
    promptExample: [
      {
        title: 'Data Extraction Assistant',
        value:
          'You are a precise data extraction assistant.\n' +
          'Your task is to read the provided text and extract a single, specific piece of information based on the instruction.Analyze this text:\n' +
          '{{original_text}}\n' +
          'Extract this specific information:\n' +
          '{{field_to_extract}}\n' +
          'Provide ONLY the extracted value as your answer. Do not include any extra words, labels, or explanations (e.g., do not write "The answer is...").\n' +
          'If the requested information cannot be found in the text, respond with the exact string "Not Found".\n',
        type: PromptType.TEXT,
        taskType: TaskType.SUBJECTIVE,
        scoringCriteria:
          'The output must be exactly the same as the reference reply, including the structure',
        useCases: [
          [
            {
              name: 'original_text',
              type: VariableType.TEXT,
              content:
                'For our Classic Chocolate Chip Cookies, preheat your oven to 375°F (190°C). Cream together 1 cup of butter and 3/4 cup of sugar. Bake for 10-12 minutes until golden brown. This recipe yields approximately 24 cookies.',
            },
            {
              name: 'field_to_extract',
              type: VariableType.TEXT,
              content: 'bake_time',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"bake_time": "10-12 minutes"}',
            },
          ],
          [
            {
              name: 'original_text',
              type: VariableType.TEXT,
              content:
                'For our Classic Chocolate Chip Cookies, preheat your oven to 375°F (190°C). Cream together 1 cup of butter and 3/4 cup of sugar. Bake for 10-12 minutes until golden brown. This recipe yields approximately 24 cookies.',
            },
            {
              name: 'field_to_extract',
              type: VariableType.TEXT,
              content: 'bake_time',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"bake_time": "10-12 minutes"}',
            },
          ],
          [
            {
              name: 'original_text',
              type: VariableType.TEXT,
              content:
                'Your flight to Tokyo (HND) is confirmed. You are flying on SkyLink Air, flight number SK451, departing from SFO on 2026-03-10 at 14:30. Your seat is 22A. Your booking confirmation code is 8K3L2P.',
            },
            {
              name: 'field_to_extract',
              type: VariableType.TEXT,
              content: 'confirmation_code',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"confirmation_code": "8K3L2P"}',
            },
          ],
          [
            {
              name: 'original_text',
              type: VariableType.TEXT,
              content:
                'Patient: John Appleseed, DOB: 1980-05-15. Admitted for observation. Vitals stable. Blood pressure is 125/80 mmHg. Current medication includes Metformin 500mg, twice daily. No signs of acute distress. Patient ID is #A789-CDE.',
            },
            {
              name: 'field_to_extract',
              type: VariableType.TEXT,
              content: 'blood_pressure',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"blood_pressure": "125/80 mmHg"}',
            },
          ],
          [
            {
              name: 'original_text',
              type: VariableType.TEXT,
              content:
                "Global Tech Inc. reported its Q3 2025 earnings today. Revenue surged to $15.2 billion, a 12% increase year-over-year. However, net profit saw a slight dip to $2.1 billion due to increased R&D spending. The company's stock symbol on the NASDAQ is GTECH.",
            },
            {
              name: 'field_to_extract',
              type: VariableType.TEXT,
              content: 'ticker',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"ticker": "GTECH"}',
            },
          ],
          [
            {
              name: 'original_text',
              type: VariableType.TEXT,
              content:
                'Introducing the new NebulaPhone X, released in 2025. It features a stunning 6.7-inch ProMotion display with a resolution of 2778x1284 pixels. The device is powered by our latest QuantumCore A17 chip and comes with a 5000mAh battery that supports fast charging. The base model is available for $1199.',
            },
            {
              name: 'field_to_extract',
              type: VariableType.TEXT,
              content: 'resolution',
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '{"resolution": "2778x1284 pixels"}',
            },
          ],
        ],
      },
      {
        title: 'Knowledge Answering Assistant',
        value:
          'You are a professional image analysis and knowledge answering assistant.\n' +
          'Your task is to provide answers based on the given image, text question, and text options.\n' +
          '## Input:\n' +
          '- Image: {{IMAGE_0}}\n' +
          '- Text Question: {{question}}\n' +
          '- Text Options: {{choices}}\n\n' +
          '## Workflow:\n' +
          '1. **Answer the Question**:\n' +
          '  1.1 Carefully examine the image, and combine it with the text question and options. Use your knowledge and analytical skills to derive the answer.\n' +
          '  1.2 Clearly document your reasoning process and thought steps.\n' +
          '  1.3 Based on your analysis, identify the option you believe to be correct as the "Your Answer".\n' +
          '## Output Format Requirements:\n' +
          'Please output only the number corresponding to the option you believe is correct (e.g., 0, 1, 2, 3, etc.). Please strictly follow the above workflow and format requirements, and output only the required number.',
        type: PromptType.MULTI,
        taskType: TaskType.OBJECTIVE,
        scoringCriteria:
          'Allow for expression differences, but the semantics must remain identical.',
        useCases: [
          [
            {
              name: 'IMAGE_0',
              type: VariableType.IMAGE,
              content: processImageUri(
                'assets/prompt/optimize-example/example-3.png',
              ),
            },
            {
              name: 'question',
              type: VariableType.TEXT,
              content: 'Which of these states is farthest north?',
            },
            {
              name: 'choices',
              type: VariableType.TEXT,
              content: "['West Virginia', 'Louisiana', 'Arizona', 'Oklahoma']",
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '0',
            },
          ],
          [
            {
              name: 'IMAGE_0',
              type: VariableType.IMAGE,
              content: processImageUri(
                'assets/prompt/optimize-example/example-2.png',
              ),
            },
            {
              name: 'question',
              type: VariableType.TEXT,
              content:
                "Identify the question that Tom and Justin's experiment can best answer.",
            },
            {
              name: 'choices',
              type: VariableType.TEXT,
              content:
                "['Do ping pong balls stop rolling along the ground sooner after being launched from a 30° angle or a 45° angle?', 'Do ping pong balls travel farther when launched from a 30° angle compared to a 45° angle?']",
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '1',
            },
          ],
          [
            {
              name: 'IMAGE_0',
              type: VariableType.IMAGE,
              content: processImageUri(
                'assets/prompt/optimize-example/example-1.png',
              ),
            },
            {
              name: 'question',
              type: VariableType.TEXT,
              content:
                "Identify the question that Kathleen and Bryant's experiment can best answer.",
            },
            {
              name: 'choices',
              type: VariableType.TEXT,
              content:
                "['Does Kathleen's snowboard slide down a hill in less time when it has a layer of wax or when it does not have a layer of wax?', 'Does Kathleen's snowboard slide down a hill in less time when it has a thin layer of wax or a thick layer of wax?']",
            },
            {
              name: 'AGENT_BUILDER_PROMPT_OUTPUT',
              type: VariableType.TEXT,
              content: '0',
            },
          ],
        ],
      },
    ] as const,
  },
};
