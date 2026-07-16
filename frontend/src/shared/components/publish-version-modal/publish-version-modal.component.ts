import {Component, EventEmitter, Inject, Input, Optional, Output, inject} from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  Validators,
} from '@angular/forms';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonUtils } from 'src/utils/common.util';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { PublishVersionSubmitSuccessComponent } from '@shared/components/version-submit-success-dialog/version-submit-component';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpaceModule } from 'ng-zorro-antd/space';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import {NzMessageService} from "ng-zorro-antd/message";
import {setSessionStorage} from "../../../utils/utils";

@Component({
  selector: 'publish-version-modal',
  templateUrl: './publish-version-modal.component.html',
  styleUrls: ['./publish-version-modal.component.scss'],
  standalone: true,
  imports: [MODULES, NzFormModule, NzInputModule, NzButtonModule, NzSpaceModule, NzTypographyModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.REVIEW],
    },
  ],
})
export class PublishVersionModalComponent {
  @Input() closeOnError = false;
  @Input() app_id = '';
  @Input() workflowType = 'chat';
  @Input() isFromDevelopSpace: boolean = false;
  @Input() app_type = '';
  @Input() from = '';
  @Input() orginWorkflowId = '';
  @Output() publishSuccess = new EventEmitter<any>();
  @Output() clickShare = new EventEmitter<any>();

  readonly modalRef = inject(NzModalRef, { optional: true });
  readonly drawerRef = inject(NzDrawerRef, { optional: true });

  versionName = '';

  public publishVersionForm: FormGroup;
  
  @Input() title = this.i18n.transform('submit_version');

  constructor(
    fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private agentDataServe: AgentDataService,
    private agentRepoServe: AppAgentRepoService,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
    private nzModal: NzModalService,
    private message: NzMessageService
  ) {
    const curTime = new Date();
    this.versionName = `v${CommonUtils.getFormattedTime(curTime)}`;

    this.publishVersionForm = fb.group({
      name: new FormControl(this.versionName, [
        Validators.required,
        Validators.minLength(1),
        Validators.maxLength(32),
      ]),
      note: new FormControl('', []),
    });
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  async onPublishClick(): Promise<void> {
    try {
      await this.publish();
    } catch {
      if(this.closeOnError) {
        this.dismiss();
      }
    }
  }

  async publish() {
    const isPass = this.checkGroup();
    if (!isPass) {
      return;
    }

    const form = this.publishVersionForm.controls;
    const params = {
      version_name: form.name.value,
      version_note: form.note.value,
    };

    this.agentDataServe.setPublishStatus('loading');

    if (['agent', 'multi'].includes(this.app_type)) {
      await this.agentRepoServe.publishAgentVersion(this.app_id, params);
      this.publishSuccess.emit();
      this.close();
      this.nzModal.create({
        nzTitle: '',
        nzFooter: null,
        nzContent: PublishVersionSubmitSuccessComponent,
        nzClassName: 'publish-version-modal-success-class',
      });
    }
    if (this.app_type === 'flow') {
      const version = await this.agentRepoServe.publishFlowVersion(
        this.app_id,
        params,
      );
      let info:any = {
        version: version,
        id: this.app_id,
      };
      if (this.from === 'edit-flow') {
        const multiFlowType = this.route.snapshot.queryParams.multiFlowType;
        if (multiFlowType) {
          info.multiFlowType = multiFlowType;
        }
        this.agentDataServe.addAgentInfo(info);
        if (this.orginWorkflowId) {
          localStorage.setItem('workflowInfo', JSON.stringify(info));
          if (multiFlowType) {
            localStorage.setItem('multiFlowTypeInfo', JSON.stringify({
              ...info,
              version_name: form.name.value,
            }));
          }
          window.history.go(-2);
          setTimeout(() => {
            window.location.reload();
          }, 0);
        } else {
          window.history.go(-2);
        }
      } else {
        this.publishSuccess.emit();
        this.close();
        this.nzModal.create({
          nzTitle: '',
          nzFooter: null,
          nzContent: PublishVersionSubmitSuccessComponent,
          nzClassName: 'publish-version-modal-success-class',
        });
      }
    }

    if (this.app_type === 'tool') {
      await this.agentRepoServe.publishPluginVersion(this.app_id, params);
      const from = this.route.snapshot.queryParams.from;
      const id = this.route.snapshot.queryParams.from_id;
      const agent_node = this.route.snapshot.queryParams.agent_node;

      if (from && (from==='flow'||from==='agent')) {
        if (from === 'flow') {
          await this.router.navigate(['/home/agent-center/app-flow/flow'], {
            queryParams: {
              id,
            },
            state: {
              currentModal: 'plugin',
              new_plugin_id: this.app_id,
              agent_node: agent_node
            },
          });
        } else if (from === 'agent') {
          setSessionStorage('pluginState',JSON.stringify({
            currentModal: 'plugin',
            new_plugin_id: this.app_id,
          }));
          await this.router.navigate(['/home/agent-center/app-agent/detail'], {
            queryParams: {
              agentId: id,
            },
          });
        }
        this.close();
        return;
      }
      this.message.create('success', this.i18n.transform('publish_success'));
    }
    this.agentDataServe.setPublishStatus('succeeded');
    this.close();
  }

  public close() {
    if (this.modalRef) {
      this.modalRef.close();
    } else if (this.drawerRef) {
      this.drawerRef.close();
    }
  }

  public dismiss() {
    if (this.modalRef) {
      this.modalRef.close();
    } else if (this.drawerRef) {
      this.drawerRef.close();
    }
  }


  private checkGroup(): boolean {
    this.publishVersionForm.markAllAsTouched();
    return this.publishVersionForm.valid;
  }
}
