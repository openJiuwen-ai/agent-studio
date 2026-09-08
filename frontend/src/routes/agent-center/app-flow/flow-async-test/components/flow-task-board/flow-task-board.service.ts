import { Injectable } from '@angular/core';
import { v4 as uuidV4 } from 'uuid';

import { IFlowChatItem } from '@routes/agent-center/types/common.types';
import CommonLogic from '@routes/app-center/common-logic-app-center';
import { FlowTaskDetailRes, FlowTaskHistory, FlowTaskStatus } from '../../flow-async-test.interface';
import { FlowAsyncExecRole } from '../../flow-async-test.constant';


@Injectable({
  providedIn: 'root',
})
export class FlowTaskBoardService {
  public parseExecHistory(execHistory: FlowTaskHistory[], taskInfo: FlowTaskDetailRes): IFlowChatItem[] {
    const thinkingStatus = [FlowTaskStatus.RUNNING, FlowTaskStatus.INIT];
    if (thinkingStatus.includes(taskInfo?.status) && !execHistory?.length) {
      return [this.createRunningChat(taskInfo)];
    }
    
    const chatLoop = [];
    let lastChat: IFlowChatItem;
    execHistory.forEach(history => {
      if (history.role.toLowerCase() === FlowAsyncExecRole.USER || !lastChat) {
        if (lastChat) {
          lastChat.thinkLoading = false;
          lastChat.thinking = false;
        }
        
        lastChat = this.createChat(history);
        chatLoop.push(lastChat);
      }

      if (history.role === FlowAsyncExecRole.ASSISTANT && lastChat) {
        this.writingToLastChat(history, taskInfo, lastChat);
      }
    });

    if (taskInfo.status === FlowTaskStatus.FAILED) {
      this.setFailChat(chatLoop, lastChat, taskInfo);
    }

    if ([FlowTaskStatus.CANCELLED, FlowTaskStatus.COMPLETED].includes(taskInfo.status) && lastChat) {
      lastChat.thinking = false;
      lastChat.thinkLoading = false;
    }

    return chatLoop;
  }

  private createChat(history: FlowTaskHistory): IFlowChatItem {
    let query = '';
    try {
      if (history.role.toLowerCase() === 'user') {
        const contentObj = JSON.parse(history.content);
        query = contentObj.query;
      }
    } catch {
      query = '';
    }

    return CommonLogic?.createFlowChatItem({
      query: query,
      dialogId: uuidV4(),
      options: {
        showAnswer: []
      }
    });
  }

  private createRunningChat(taskInfo: FlowTaskDetailRes): IFlowChatItem {
    return CommonLogic?.createFlowChatItem({
      query: taskInfo?.inputs?.query,
      dialogId: uuidV4(),
      options: {
        showAnswer: []
      }
    });
  }

  private setFailChat(chatLoop: IFlowChatItem[], lastChat: IFlowChatItem, taskInfo: FlowTaskDetailRes): void {
    const showAnswer = [{
      text: taskInfo.message,
    }];

    if (lastChat) {
      lastChat.showAnswer = lastChat.showAnswer?.length ? lastChat.showAnswer : showAnswer;
      lastChat.thinkLoading = false;
      lastChat.thinking = false;
      return;
    }
    chatLoop.push(
      CommonLogic?.createFlowChatItem({
        query: taskInfo?.inputs?.query,
        dialogId: uuidV4(),
        options: {
          showAnswer: showAnswer,
          thinkLoading: false
        }
      })
    );
  }

  private writingToLastChat(history: FlowTaskHistory, taskInfo: FlowTaskDetailRes, lastChat: IFlowChatItem): void {
    try {
      // content为JSON字符串
      const contentObj = JSON.parse(history.content);
      if (typeof contentObj !== 'object') {
        throw new Error();
      }
      const inputList = contentObj?.inputs;
      inputList.forEach(input => {
        input.uniqueId = input.name
      });
      
      // PENDING状态下才展示输入
      if (taskInfo.status === FlowTaskStatus.PENDING) {
        lastChat.showAnswer.push({
          text: '',
          isShowInputParams: true,
          inputList: inputList
        });
      } else {
        // 非PENDING（COMPLETED/FAILED等）+ content 是合法 {"inputs":...} JSON：按原文展示，与 catch 路径一致
        lastChat.showAnswer.push({
          text: history.content
        });
      }
    } catch (e) {
      // content为普通字符串
      lastChat.showAnswer.push({
        text: history.content,
      });
    }
    
    if (lastChat.showAnswer.length > 0) {
      lastChat.thinking = false;
      lastChat.thinkLoading = false;
    }
  }
}
