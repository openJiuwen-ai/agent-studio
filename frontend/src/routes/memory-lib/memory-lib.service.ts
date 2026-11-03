import { Injectable, signal, inject, ApplicationRef, createComponent, EnvironmentInjector } from '@angular/core';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { MemoryLibDeleteModalComponent } from '@routes/memory-lib/components/memory-lib-delete-modal/memory-lib-delete-modal.component';
import { MemoryLibReferenceHalfmodalComponent } from '@routes/memory-lib/components/memory-lib-reference-halfmodal/memory-lib-reference-halfmodal.component';
import { MemoryLibSelectorHalfmodalComponent } from '@routes/memory-lib/components/memory-lib-selector-halfmodal/memory-lib-selector-halfmodal.component';
import { SelectMemoryCreateTypeComponent } from '@routes/memory-lib/components/select-memory-create-type/select-memory-create-type.component';
import { ConnectExternalMemoryModalComponent } from '@routes/memory-lib/components/connect-external-memory-modal/connect-external-memory-modal.component';
import { MemoryLibApiService } from '@routes/memory-lib/memory-lib-api.service';
import { MemoryLibCreationHalfmodalComponent } from '@routes/memory-lib/memory-lib-creation-halfmodal/memory-lib-creation-halfmodal.component';
import { IMemoryLibCreationData, IMemoryLibItem, IMemoryLibSelectData } from '@routes/memory-lib/memory-lib-interfaces';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { I18NextEagerPipe } from 'angular-i18next';

@Injectable({
  providedIn: 'any',
})
export class MemoryLibService {
  readonly nzDrawerService = inject(NzDrawerService);
  readonly nzModalService = inject(NzModalService);
  readonly nzMessageService = inject(NzMessageService);
  readonly commonService = inject(CommonService);
  readonly memoryLibApiService = inject(MemoryLibApiService);
  readonly i18n = inject(I18NextEagerPipe);
  private readonly appRef = inject(ApplicationRef);
  private readonly envInjector = inject(EnvironmentInjector);

  subscribeBtnDisabled = signal(false);

  constructor(private readonly http: HttpService) {
    this.subscription();
  }

  subscription() {}

  /**
   * 创建或者编辑记忆库
   * @param callBack
   * @param memoryLibId
   */
  createOrEditMemLib(callBack: (data: IMemoryLibCreationData) => void, memoryLibId = '') {
    const drawerRef = this.nzDrawerService.create({
      nzContent: MemoryLibCreationHalfmodalComponent,
      nzWidth: '700px',
      nzMask: true,
      nzContentParams: {
        libId: memoryLibId,
      },
      nzData: {
        libId: memoryLibId,
        beforeHide: ({ reason }) => {
          const creatioComp: MemoryLibCreationHalfmodalComponent = drawerRef.getContentComponent();
          const { basicInfoFormGroup, ltmRetrievalStrategyFormGroup, extractionFrequencyFormGroup, setLoading } = creatioComp;
          if (reason) {
            const errors = [basicInfoFormGroup?.invalid, ltmRetrievalStrategyFormGroup?.invalid, extractionFrequencyFormGroup?.invalid].filter(Boolean);
            if (!errors.length) {
              const frequencyValues = extractionFrequencyFormGroup.getRawValue();
              callBack({
                reason,
                halfModalRef: drawerRef as any,
                data: {
                  ...basicInfoFormGroup.getRawValue(),
                  long_term_memory_strategies: ltmRetrievalStrategyFormGroup.getRawValue().ltmRetrievalStrategy ?? [],
                  conversation_round: frequencyValues.conversation_round ?? undefined,
                  time_span: frequencyValues.time_span ?? undefined,
                  memory_backend_type: creatioComp.memoryBackendType(),
                  memory_service_instance_id: creatioComp.memoryServiceInstanceId(),
                },
                setLoading,
              });
            }
          } else {
            callBack({
              reason,
              halfModalRef: drawerRef as any,
              data: null,
              setLoading,
            });
          }
        },
      },
    });
  }

  /**
   * 记忆库选择弹窗
   * @param existedLibs
   * @param callBack
   */
  showMemoryLibSelector(existedLibs: IMemoryLibItem[], callBack: (data: IMemoryLibSelectData) => void): void {
    const drawerRef = this.nzDrawerService.create({
      nzContent: MemoryLibSelectorHalfmodalComponent,
      nzWidth: '700px',
      nzMask: true,
      nzData: {
        existedLibs,
        beforeHide: ({ reason }: { reason: boolean }) => {
          if (reason) {
            const selectorComp: MemoryLibSelectorHalfmodalComponent = drawerRef.getContentComponent() as MemoryLibSelectorHalfmodalComponent;
            const { existedMemoryLibs } = selectorComp;
            callBack({
              reason,
              halfModalRef: drawerRef as any,
              data: existedMemoryLibs(),
            });
            drawerRef.close();
          } else {
            callBack({
              reason,
              halfModalRef: drawerRef as any,
              data: [],
            });
            drawerRef.close();
          }
        },
      },
    });
  }

  /**
   * 记忆库引用弹窗
   * @param memLibId
   */
  showReference(memLibId: string): void {
    this.nzDrawerService.create({
      nzContent: MemoryLibReferenceHalfmodalComponent,
      nzWidth: '700px',
      nzMask: true,
      nzData: {
        memLibId,
      },
    });
  }

  /**
   * 单记忆库删除（自带引用判断封装）
   * @param memoryLib
   * @return 是否删除成功（取消列为删除失败）
   */
  safeDeleteMemoryLib(memoryLib: IMemoryLibItem): Promise<boolean> {
    return new Promise(resolve => {
      const myModal = this.nzModalService.create({
        nzContent: MemoryLibDeleteModalComponent,
        nzData: {
          deletedMemoryLib: memoryLib,
        },
        nzOnOk: (instance: MemoryLibDeleteModalComponent) => {
          return new Promise<boolean>(resolveP => {
            const { setLoading, checkTemplateForm } = instance;
            if (!checkTemplateForm()) {
              setLoading(true);
              this.memoryLibApiService
                .deleteMemory(memoryLib.memory_repo_id)
                .then(() => {
                  this.nzMessageService.success(this.i18n.transform('memory.management.modal.deleteTip'));
                  setLoading(false);
                  resolve(true);
                  resolveP(true);
                })
                .catch(() => {
                  setLoading(false);
                  resolveP(false);
                });
            } else {
              resolveP(false);
            }
          });
        },
        nzOnCancel: () => {
          resolve(false);
          return true;
        },
      });
      const content = myModal.getContentComponent();
      content.deletedMemoryLib = memoryLib;
    });
  }

  /**
   * 弹出选择创建类型 Modal（内置 / 外部）
   * 根据用户选择分别走内置创建或外部连接流程。
   * 通过动态创建组件实例并调用其 showWithCallback 方法，
   * 复用组件自身的 modal 模板（title/footer/content）。
   */
  showSelectCreateType(callBack: (data: IMemoryLibCreationData) => void) {
    // Create a detached component instance so we can use its template refs.
    const compRef = createComponent(SelectMemoryCreateTypeComponent, { environmentInjector: this.envInjector });
    this.appRef.attachView(compRef.hostView);
    compRef.instance.showWithCallback(key => {
      if (key === 'builtin') {
        this.createOrEditMemLib(callBack);
      } else if (key === 'external') {
        this.connectExternalMemoryLib(callBack);
      }
      // Cleanup: destroy the detached component after modal closes.
      setTimeout(() => {
        this.appRef.detachView(compRef.hostView);
        compRef.destroy();
      }, 0);
    });
  }

  /**
   * 打开"连接外部记忆库" Drawer 表单
   */
  connectExternalMemoryLib(callBack: (data: IMemoryLibCreationData) => void) {
    const drawerRef = this.nzDrawerService.create({
      nzContent: ConnectExternalMemoryModalComponent,
      nzWidth: '700px',
      nzMask: true,
      nzContentParams: {},
      nzData: {
        beforeHide: ({ reason }) => {
          if (reason) {
            const comp: ConnectExternalMemoryModalComponent = drawerRef.getContentComponent();
            if (comp.basicInfoFormGroup.invalid || comp.instanceFormGroup.invalid) {
              return;
            }
            callBack({
              reason: true,
              halfModalRef: drawerRef as any,
              data: comp.getFormData(),
              setLoading: comp.loading.set.bind(comp.loading),
            });
          } else {
            callBack({
              reason: false,
              halfModalRef: drawerRef as any,
              data: null,
              setLoading: () => {},
            });
          }
        },
      },
    });
  }
}
