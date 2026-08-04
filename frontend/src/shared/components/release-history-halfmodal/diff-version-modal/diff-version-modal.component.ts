import { ChangeDetectorRef, Component, Input, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaskComponent } from '../../../../utils/mask.component';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { I18nNamespace } from '@i18n';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';

@Component({
  selector: 'diff-version-modal',
  templateUrl: './diff-version-modal.component.html',
  styleUrls: ['./diff-version-modal.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, MODULES, MonacoEditorModule, NzSelectModule, NzTagModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.REVIEW],
    },
  ],
})
export class DiffVersionModalComponent {
  @Input() app_id = '';
  @Input() versionList: any[] = [];
  @Input() leftIndex = 0;
  @Input() rightIndex = 0;
  @Input() type = 'agent';

  lineAdd = 0;
  lineDel = 0;
  height = 500;

  originalValue = '';
  modifiedValue = '';

  leftSelectedId = 'latest';
  rightSelectedId = 'latest';
  leftOptions: VersionOption[] = [];
  rightOptions: VersionOption[] = [];

  diffOptions = {
    enableSplitViewResizing: true,
    renderSideBySide: true,
    renderIndicators: true,
    language: 'json',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    isInEmbeddedEditor: false,
  };

  constructor(
    private agentRepoServe: AppAgentRepoService,
    private appFlowRepoServ: AppFlowRepoService,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone
  ) {}

  async ngOnInit() {
    const currentLabel = this.i18n.transform('current');
    const versionOptions: VersionOption[] = (this.versionList || []).map(item => ({
      id: item.version_id,
      label: item.version_name,
    }));
    const headOption: VersionOption = { id: 'latest', label: currentLabel };

    this.leftOptions = [headOption, ...versionOptions];
    this.rightOptions = [headOption, ...versionOptions];
    this.leftSelectedId = this.leftOptions[this.leftIndex + 1].id;
    this.rightSelectedId = this.rightOptions[this.rightIndex + 1].id;

    this.ngZone.run(() => MaskComponent.show());
    try {
      const [originalData, modifiedData] = await Promise.all([this.getVersionData(this.leftSelectedId), this.getVersionData(this.rightSelectedId)]);
      this.ngZone.run(() => {
        this.originalValue = JSON.stringify(originalData, null, 2);
        this.modifiedValue = JSON.stringify(modifiedData, null, 2);
        MaskComponent.hide();
        this.cdr.detectChanges();
      });
    } catch (error) {
      this.ngZone.run(() => {
        MaskComponent.hide();
        this.cdr.detectChanges();
      });
    }
  }

  onDiffInit(editor: any) {
    if (!editor?.onDidUpdateDiff) {
      return;
    }
    editor.onDidUpdateDiff(() => {
      const changes = editor.getLineChanges?.() ?? [];
      const { lineAdd, lineDel } = this.calcChangeLines(changes);
      this.ngZone.run(() => {
        this.height = Math.min(((this.modifiedValue || '').split('\n').length + lineDel) * 19 + 100, document.documentElement.clientHeight * 0.7);
        this.lineAdd = lineAdd;
        this.lineDel = lineDel;
        this.cdr.detectChanges();
      });
    });
  }

  async changeLeft(id: string) {
    this.leftSelectedId = id;
    this.ngZone.run(() => MaskComponent.show());
    try {
      const data = await this.getVersionData(id);
      this.ngZone.run(() => {
        this.originalValue = JSON.stringify(data, null, 2);
        MaskComponent.hide();
        this.cdr.detectChanges();
      });
    } catch (error) {
      this.ngZone.run(() => {
        MaskComponent.hide();
        this.cdr.detectChanges();
      });
    }
  }

  async changeRight(id: string) {
    this.rightSelectedId = id;
    this.ngZone.run(() => MaskComponent.show());
    try {
      const data = await this.getVersionData(id);
      this.ngZone.run(() => {
        this.modifiedValue = JSON.stringify(data, null, 2);
        MaskComponent.hide();
        this.cdr.detectChanges();
      });
    } catch (error) {
      this.ngZone.run(() => {
        MaskComponent.hide();
        this.cdr.detectChanges();
      });
    }
  }

  private async getVersionData(versionId: string) {
    let details: any = {};
    const isAgent = this.type === 'multi' || this.type === 'agent';
    try {
      let value: any;
      if (versionId !== 'latest') {
        value = isAgent
          ? await this.agentRepoServe.rollbackAgentVersion(this.app_id, versionId)
          : await this.agentRepoServe.rollbackFlowVersion(this.app_id, versionId);
        if (isAgent) {
          value.workflow_details = value.details;
          value.avatar = value.icon;
        }
      } else if (isAgent) {
        value = await this.agentRepoServe.getMultiAgent(this.app_id);
        value.workflow_details = value.details;
        value.avatar = value.icon;
      } else {
        value = await this.appFlowRepoServ.getFlow(this.app_id);
      }
      details = value.workflow_details;
    } catch {
      // do nth
    }
    return details;
  }

  private calcChangeLines(changes: any[]) {
    let lineAdd = 0;
    let lineDel = 0;
    (changes || []).forEach(change => {
      if (change.modifiedEndLineNumber && change.modifiedStartLineNumber) {
        lineAdd += change.modifiedEndLineNumber - change.modifiedStartLineNumber + 1;
      }
      if (change.originalEndLineNumber && change.originalStartLineNumber) {
        lineDel += change.originalEndLineNumber - change.originalStartLineNumber + 1;
      }
    });
    return { lineAdd, lineDel };
  }
}

interface VersionOption {
  id: string;
  label: string;
}
