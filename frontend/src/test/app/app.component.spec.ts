describe('message manage test', () => {
  interface ConversationData {
    messages?: Message[];
    task_name?: string;
    task_status?: number;
    task_run_mode?: number;
    next_key?: string;
    run_time?: number;
    agent_list?: Agent[];
  }

  interface Message {
    id: string;
    task_id: string;
    type: number;
    content: string;
    steps: Step[];
    file_list: File[];
    create_time: number;
  }

  interface Action {
    stepId: string;
    action_id: string;
    content: string;
    display_content: string;
    file_list: File[];
    create_time: number;
    action_type: string;
    tool_type: string;
  }

  interface Step {
    agent_name: string;
    step_id: string;
    answer_id: string;
    action_list: Action[];
    create_time: number;
    is_finish: boolean;
  }

  interface Agent {
    id: string;
    name: string;
    deleted: boolean;
    type: string;
    description: string;
    logo: string;
    instructions: string;
    prologue: string;
    created_date: string;
    created_by_user_id: string;
    last_updated_date: string;
    last_updated_by_user_id: string;
    tenant_id: string;
    dept_code: string;
    agent_work_type: string;
    suggest_query: string[];
    model_id: string;
    is_enable: boolean;
    asset_status: string;
  }

  interface File {
    id: string;
    name: string;
    koo_page_id: string;
    task_id?: string;
    isHover?: boolean;
    action_id?: string;
    type?: string;
    time?:string
  }

  interface RenderDataObj {
    following?: Follow;
    pause?: Plan[];
    plan?: Plan[];
    browser?: Browser[];
    file?: File[];
  }

  interface RenderData {
    following: Follow[];
    pause: Plan[];
    plan: Plan[];
    browser: Browser[];
    file: File[];
  }


  interface Follow {
    file: File[];
    browser: Browser[];
    plan: Plan[];
    pause: Plan[];
  }

  interface Browser {
    name?: string;
    number?: string;
    time?: string;
    details?: BrowserDetails[];
    value?:any;
    url?:any
  }

  interface BrowserDetails {
    name: string;
    url: string;
  }

  interface Plan {
    name: string;
    details: Detail[];
  }

  interface Detail {
    status: string;
    value: confirmData[];
  }

  interface confirmData {
    name: string;
    type: string;
    allow_modification: boolean;
    options: Option[];
  }

  interface Option {
    value: string;
    default: boolean;
  }

  enum taskStatusMap {
    "unStart" = 0,
    "running" = 1,
    "wait0" = 2,
    "waiting" = 3,
    "waited" = 4,
    "wait2" = 5,
    "delete" = 6,
    "success" = 7,
    "fail" = 8,
    "ending" = 9,
    "end" = 10
  }

  it('just test', function () {
    const result = 111;
    expect(111).toEqual(result);
  });

  it('manage message data to render', function () {
    // mock 初始值
    const mockInitMessageData: ConversationData = {
      messages: [
        {
          id: '0175ec1cf2544408b938ddc14548dbf0',
          task_id: 'e40d8a9755d046a686fedfa0225f3ad3',
          type: 2,
          content: '南京未来3天天气情况',
          steps: [
            {
              agent_name: 'react_agent',
              step_id: '0ae97290-3a02-11f0-8733-e2cb1ae62147',
              answer_id: '0175ec1cf2544408b938ddc14548dbf0',
              action_list: [
                {
                  stepId: '0ae97290-3a02-11f0-8733-e2cb1ae62147',
                  action_id: '0175ec1cf2544408b938ddc14548dbf0',
                  content: '南京未来3天天气情况',
                  display_content:
                    '{"confirm_data":[{"name":"报告标题","type":"single-choice","allow_modification":false,"options":[{"value":"人工智能在生物领域应用的深度研究","default":true}],"suggestion":"开始任务"}',
                  file_list: [
                    {
                      id: 'e30b8581c3a14939897575a01ab5b93c',
                      name: '任务资源消耗.md',
                      koo_page_id: '9dd7ec99-c112-4fe0-a751-8970291d9fe2'
                    }
                  ],
                  create_time: 1,
                  action_type: 'action_type',
                  tool_type: 'tool_type'
                },
                {
                  stepId: '8f359bc6-4ba8-11f0-b817-be26120b2990',
                  action_id: '98f2c334-4ba8-11f0-a783-be26120b2990',
                  content: '{"input": {"query": "机器学习 药物开发 案例"}}',
                  display_content:
                    '{"output": [{"type": "tool_result", "id": "call_8c43f55974414c09abae5d", "output": [{"type": "text", "text": "[\\n    {\\n        \\"url\\": \\"https://www.doc88.com/p-21899643819811.html\\",\\n    }\\n]", "annotations": null}], "name": "web_search"}]}',
                  file_list: [
                    {
                      id: 'e30b8581c3a14939897575a01ab5b93c',
                      name: '任务资源消耗.md',
                      koo_page_id: '9dd7ec99-c112-4fe0-a751-8970291d9fe2'
                    }
                  ],
                  create_time: 1750184796386,
                  action_type: 'tool_use',
                  tool_type: 'web_search'
                }
              ],
              create_time: 1748244003540,
              is_finish: false
            }
          ],
          file_list: [
            {
              id: 'e30b8581c3a14939897575a01ab5b93c',
              name: '任务资源消耗.md',
              koo_page_id: '9dd7ec99-c112-4fe0-a751-8970291d9fe2'
            }
          ],
          create_time: 1748244003540
        }
      ],
      task_name: 'Task 1',
      task_run_mode: 1,
      task_status: 1,
      next_key: '2e4ceebddde5422cb20df81c2e3d047d',
      run_time: 100,
      agent_list: [
        {
          id: '835c5e0bf3a3407ebe9d2eac977f39f2',
          name: 'Agent助手',
          deleted: false,
          type: 'Agent',
          description: 'this is test',
          logo: 'logo',
          instructions: '',
          prologue: 'this is test',
          created_date: '2025/05/26 15:15:53',
          created_by_user_id: '0000000000000000001',
          last_updated_date: '2025/05/26 15:20:17',
          last_updated_by_user_id: '0000000000000000002',
          tenant_id: '0000000000000000003',
          dept_code: '2aa7054863b54573b5f2e4f4ee3ab359',
          agent_work_type: 'agent_operator',
          suggest_query: ['如何利用小学教学助手提高学生的学习兴趣'],
          model_id: 'integrate:2aa7054863b54573b5f2e4f4ee3ab359:DeepSeek-V3',
          is_enable: true,
          asset_status: '0'
        }
      ]
    };
    // 处理结果值
    const mockResultRenderData: RenderDataObj = {};

    const handleMessages = (convData: ConversationData) => {
      if (!convData.messages || convData.messages.length <= 0 || !Array.isArray(convData.messages)) {
        return;
      }
      if (convData.messages.length % 2 !== 0) {
        // 说明此时答案数据还没有返回
        return;
      }
      if (convData.messages.length % 2 === 0) {
        // 说明此时答案数据已经返回了
        if (convData.messages[convData.messages.length - 1].steps.length <= 0) {
          // 但是步骤还没有生成
          return;
        }
        if (convData.messages[convData.messages.length - 1].steps.length > 0) {
          initConvData(convData.messages[convData.messages.length - 1]);
          // 此时步骤数据已经生成了
          handleMessageData(convData);
        }
      }
    };

    const resultData: RenderDataObj = {
      following: {
        file: [],
        browser: [],
        plan: [],
        pause: []
      },
      pause: [],
      plan: [],
      browser: []
    };
    let currentTaskId = '';
    let currentStatus = '';
    const actionAndStepIdsData: any[] = [];
    const types = [
      {
        label: '轨迹追踪',
        name: 'Following',
        isSelected: true,
        isShow: true
      },
      {
        label: '计划',
        name: 'Plan',
        isSelected: false,
        isShow: false
      },
      {
        label: '浏览器',
        name: 'Browser',
        isSelected: false,
        isShow: false
      },
      {
        label: '文件',
        name: 'File',
        isSelected: false,
        isShow: false
      }
    ];

    const initConvData = (messageData: Message) => {
      if (messageData.task_id !== currentTaskId) {
        setDataInit();
        currentTaskId = messageData.task_id;
        actionAndStepIdsData.length = 0;
        currentStatus = '';
      }
    };

    const setDataInit = () => {
      resultData.following.file = [];
      resultData.following.browser = [];
      resultData.following.plan = [];
      resultData.following.pause = [];
      resultData.pause = [];
      resultData.plan = [];
      resultData.browser = [];
      for (let index = 0; index < types.length; index++) {
        types[index].isSelected = false;
        types[index].isShow = false;
      }
      types[0].isShow = true;
      types[0].isSelected = true;
    };

    const handleMessageData = (convData: ConversationData) => {
      if (!convData || !Array.isArray(convData.messages)) {
        return;
      }
      const messageData: Message[] = convData.messages;
      for (let index = 0; index < messageData.length; index++) {
        handleStepSData(messageData[index].steps, convData);
      }
      if (convData.task_status === taskStatusMap.wait2) {
        // 用户暂停当前数据
        return;
      }
      if (
        convData['task_status'] === taskStatusMap.wait2 ||
        convData['task_status'] === taskStatusMap.delete ||
        convData['task_status'] === taskStatusMap.success ||
        convData['task_status'] === taskStatusMap.fail ||
        convData['task_status'] === taskStatusMap.ending ||
        convData['task_status'] === taskStatusMap.ending
      ) {
        currentStatus = 'file';
        setTypesShowData(convData);
      }
    };

    const setTypesShowData = (convData: ConversationData) => {
      const planStatus = types[1].isShow;
      if (currentStatus === 'file' || currentStatus === 'code') {
        for (let index = 0; index < types.length; index++) {
          types[index].isShow = true;
        }
        types[1].isShow = planStatus;
      } else if (currentStatus === 'browser') {
        types[2].isShow = true;
      } else if (currentStatus === 'plan' || currentStatus === 'pause') {
        // 规划模式
        types[1].isShow = true;
      }
      if (convData.task_run_mode === 0) {
        types[1].isShow = false;
      }
    };

    const handleStepSData = (stepsData: Step[], convData: ConversationData) => {
      if (!Array.isArray(stepsData)) {
        return;
      }
      for (let index = 0; index < stepsData.length; index++) {
        const actionData = stepsData[index].action_list;
        for (let actionIndex = 0; actionIndex < actionData.length; actionIndex++) {
          if (stepsData[index].agent_name !== 'planning_agent') {
            setPlanStatus(actionData[actionIndex], convData);
          }
          if (
            actionData[actionIndex].tool_type === 'web_search' &&
            actionData[actionIndex].display_content &&
            actionData[actionIndex].content
          ) {
            currentStatus = 'browser';
            setTypesShowData(convData);
            getWebSearchData(actionData[actionIndex], stepsData[index]);
          } else if (
            actionData[actionIndex].tool_type === 'file_write' ||
            actionData[actionIndex].tool_type === 'gen_web' ||
            actionData[actionIndex].tool_type === 'file_read' ||
            actionData[actionIndex].tool_type === 'gen_report'
          ) {
            const taskId = convData.messages[convData.messages.length - 1].task_id;
            getFileData(actionData[actionIndex], taskId, convData);
          } else if (actionData[actionIndex].tool_type === 'plan') {
            getPlanData(actionData[actionIndex], convData);
          }
        }
      }
    };

    const setPlanStatus = (actionData: Action, convData: ConversationData) => {
      if (convData.task_run_mode === 0) {
        types[1].isShow = false;
        return;
      }
      if (actionData.action_type === 'step_start') {
        try {
          const title = JSON.parse(actionData.content).title;
          let isDetailContainTitle = false;
          let containIndex = -1;
          for (let index = 0; index < resultData.following.plan[0].details.length; index++) {
            if (title.indexOf(resultData.following.plan[0].details[index].value) !== -1) {
              isDetailContainTitle = true;
              containIndex = index;
              break;
            }
          }
          if (!isDetailContainTitle) {
            return;
          }
          resultData.following.plan[0].details[containIndex].status = 'running';
          currentStatus = 'running';
        } catch (e) {
        }
      } else if (actionData.action_type === 'reply') {
        try {
          const title = JSON.parse(actionData.content).title;
          if (title !== '当前Step已完成！') {
            return;
          }
          const filterData = resultData.following.plan[0].details.filter((item: Detail) => item.status === 'running');
          if (filterData.length <= 0) {
            return;
          }
          filterData[0].status = 'finish';
        } catch (e) {
        }
      }
      resultData.plan = resultData.following.plan;
    };

    // 处理webSearch的数据
    const getWebSearchData = (actionData: Action, stepData: Step) => {
      try {
        const contentData = JSON.parse(actionData.content);
        const displayContentData = JSON.parse(actionData.display_content);
        const textData = JSON.parse(displayContentData.output[0].output[0].text);
        if (actionAndStepIdsData.indexOf(stepData.step_id + actionData.action_id) !== -1) {
          return;
        }
        const browserData:Browser = {
          name: contentData.input.query,
          number: `${textData.length}个结果`,
          time: getTime(actionData.create_time),
          details: []
        };
        for (let index = 0; index < textData.length; index++) {
          resultData.following.browser.push({
            value: textData[index].description,
            url: textData[index].url
          });
          browserData.details.push({
            name: textData[index].description,
            url: textData[index].url
          });
        }
        resultData.browser.push(browserData);
        actionAndStepIdsData.push(stepData.step_id + actionData.action_id);
      } catch (e) {
      }
    };

    const getTime = (timeStamp: number) => {
      const date = new Date(timeStamp);
      const hours = date.getHours();
      const minutes = date.getMinutes();
      const formattedHours = String(hours).padStart(2, '0');
      const formattedMinutes = String(minutes).padStart(2, '0');
      return `${formattedHours}:${formattedMinutes}`;
    };

    const getPlanData = (actionData: Action, convData: ConversationData) => {
      try {
        if (actionData.display_content) {
          let displayContent = JSON.parse(actionData.display_content)['plan_list']['confirm_data'];
          let isOldData = false; // 兼容旧的数据

          if (!displayContent) {
            isOldData = true;
            displayContent = JSON.parse(actionData.display_content)['plan_list'];
          }

          if (!Array.isArray(displayContent)) {
            return;
          }

          const filterData = displayContent.filter((item) => item['is_track']);
          if (filterData.length <= 0 && !isOldData) {
            return;
          }

          currentStatus = 'plan';
          setTypesShowData(convData);

          const flatMapArr = filterData.flatMap((obj) => obj.confirm);
          if (flatMapArr.length <= 0 && !isOldData) {
            return;
          }

          resultData.following.plan.length = 0;
          resultData.following.plan.push({
            name: '分析和制定的计划结果',
            details: []
          });
          if (!isOldData) {
            for (let index = 0; index < flatMapArr.length; index++) {
              resultData.following.plan[0].details.push({
                status: 'noStart',
                value: flatMapArr[index]
              });
            }
          }
          if (isOldData) {
            for (let index = 0; index < displayContent.length; index++) {
              resultData.following.plan[0].details.push({
                status: 'noStart',
                value: displayContent[index]
              });
            }
          }
          resultData.plan = resultData.following.plan;
        }
      } catch (e) {
      }
    };

    const getFileData = (actionData: Action, taskId: string, convData: ConversationData) => {
      if (actionData.file_list && actionData.file_list.length > 0) {
        const fileIds = Array.from(resultData.following.file, (item) => item.id);
        for (let index = 0; index < actionData['file_list'].length; index++) {
          if (fileIds.indexOf(actionData['file_list'][index].id) === -1) {
            currentStatus = 'code';
            setTypesShowData(convData);
            resultData.following.file.push({
              id: actionData['file_list'][index].id,
              name: actionData['file_list'][index].name,
              type: getFileType(actionData['file_list'][index]),
              time: getTime(actionData.create_time),
              isHover: false,
              task_id: taskId,
              action_id: actionData['action_id'],
              koo_page_id: actionData['file_list'][index]['koo_page_id'] || ''
            });
          } else {
            // 如果数据重复就用新的数据替换旧的数据
            let findIndex = resultData.following.file.findIndex(
              (item) => item.id === actionData.file_list[index].id
            );
            if (findIndex >= 0) {
              resultData.following.file[findIndex].id = actionData.file_list[index].id;
              resultData.following.file[findIndex].name = actionData['file_list'][index].name;
              resultData.following.file[findIndex].time = getTime(actionData.create_time);
              resultData.following.file[findIndex].type = getFileType(actionData.file_list[index]);
              resultData.following.file[findIndex].isHover = false;
              resultData.following.file[findIndex].task_id = taskId;
              resultData.following.file[findIndex].action_id = actionData.action_id;
              resultData.following.file[findIndex]['koo_page_id'] =
                actionData.file_list[index].koo_page_id || '';
            }
          }
        }
      }
    };

    const getFileType = (fileData: File) => {
      if (fileData.name.endsWith('md')) {
        return 'markdown';
      }
      if (fileData.name.endsWith('jsx')) {
        return 'jsx';
      }
      if (fileData.name.endsWith('zip')) {
        return 'zip';
      }
      return 'markdown';
    };

    handleMessages(mockInitMessageData);

    expect(resultData).toEqual(mockResultRenderData);
  });
});
