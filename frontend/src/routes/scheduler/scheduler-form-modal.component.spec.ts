import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { of } from 'rxjs';

import { SchedulerFormModalComponent } from './scheduler-form-modal.component';
import { SchedulerService } from './scheduler.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { ModelManagementService } from '@services/repositories/model-management-new';

describe('SchedulerFormModalComponent - onSubmit', () => {
  let fixture: ComponentFixture<SchedulerFormModalComponent>;
  let component: SchedulerFormModalComponent;
  let schedulerService: any;
  let message: any;

  const setup = async (modalData: any = { editTask: null }) => {
    schedulerService = {
      getWorkspaceId: () => 'ws-1',
      createTask: jasmine.createSpy('createTask').and.returnValue(of({})),
      updateTask: jasmine.createSpy('updateTask').and.returnValue(of({})),
    };
    message = {
      warning: jasmine.createSpy('warning'),
      success: jasmine.createSpy('success'),
      error: jasmine.createSpy('error'),
    };
    await TestBed.configureTestingModule({
      imports: [SchedulerFormModalComponent],
      providers: [
        { provide: NzModalRef, useValue: { close: jasmine.createSpy('close') } },
        { provide: NzMessageService, useValue: message },
        { provide: SchedulerService, useValue: schedulerService },
        {
          provide: AppAgentRepoService,
          useValue: {
            getAgentList: jasmine.createSpy('getAgentList').and.resolveTo({
              agent_list: [{ agent_id: 'a-1', name: '智能体1' }],
            }),
            getWorkflowList: jasmine.createSpy('getWorkflowList').and.resolveTo({ workflow_list: [] }),
          },
        },
        { provide: AppFlowRepoService, useValue: { getFlow: jasmine.createSpy('getFlow').and.resolveTo({}) } },
        {
          provide: ModelManagementService,
          useValue: { getAvailableModelList: jasmine.createSpy('getAvailableModelList').and.resolveTo({ data: [] }) },
        },
        { provide: NZ_MODAL_DATA, useValue: modalData },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(SchedulerFormModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  it('agent_run：参数齐全时应调用 createTask，payload 带 agent_id 和 query', async () => {
    await setup();
    component.form.patchValue({
      name: '测试任务',
      executorType: 'agent_run',
      agentId: 'a-1',
      prompt: '生成日报',
      scheduleRule: { type: 'cron', cronExpression: '0 9 * * *' },
    });
    component.onSubmit();
    expect(schedulerService.createTask).toHaveBeenCalledTimes(1);
    const payload = schedulerService.createTask.calls.mostRecent().args[0];
    expect(payload.executor).toEqual({ type: 'agent_run', config: { agent_id: 'a-1', query: '生成日报' } });
    expect(payload.schedule).toEqual({ type: 'cron', config: { expression: '0 9 * * *' } });
    expect(payload.workspace_id).toBe('ws-1');
  });

  it('agent_run：未选智能体时应拦截且不创建', async () => {
    await setup();
    component.form.patchValue({
      name: '测试任务',
      executorType: 'agent_run',
      prompt: '生成日报',
      scheduleRule: { type: 'cron', cronExpression: '0 9 * * *' },
    });
    component.onSubmit();
    expect(message.warning).toHaveBeenCalledWith('请选择智能体');
    expect(schedulerService.createTask).not.toHaveBeenCalled();
  });

  it('workflow_run：payload 应带 workflow_id 和 inputs', async () => {
    await setup();
    component.workflowInputParams = [{ name: 'query', required: true, type: 'string' }];
    component.workflowInputs = { query: '内容' };
    component.form.patchValue({
      name: 'wf任务',
      executorType: 'workflow_run',
      workflowId: 'wf-1',
      scheduleRule: { type: 'cron', cronExpression: '0 9 * * *' },
    });
    component.onSubmit();
    expect(schedulerService.createTask).toHaveBeenCalledTimes(1);
    const payload = schedulerService.createTask.calls.mostRecent().args[0];
    expect(payload.executor).toEqual({
      type: 'workflow_run',
      config: { workflow_id: 'wf-1', inputs: { query: '内容' } },
    });
  });

  it('任务名为空（form invalid）时不应发请求', async () => {
    await setup();
    component.form.patchValue({
      executorType: 'agent_run',
      agentId: 'a-1',
      prompt: 'x',
      scheduleRule: { type: 'cron', cronExpression: '0 9 * * *' },
    });
    component.onSubmit();
    expect(schedulerService.createTask).not.toHaveBeenCalled();
  });
});
