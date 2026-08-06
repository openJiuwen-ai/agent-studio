import { Component, Input, Inject } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { AddPluginsComponent } from '@routes/agent-center/app-agent/components/add-plugins/add-plugins.component';
import { NzDrawerRef, NZ_DRAWER_DATA } from 'ng-zorro-antd/drawer';

@Component({
  selector: 'meta-add-plugin-halfmodal',
  standalone: true,
  imports: [MODULES, AddPluginsComponent],
  templateUrl: './add-plugin-halfmodal.component.html',
  styleUrls: ['./add-plugin-halfmodal.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class AddPluginHalfmodalComponent {
  @Input() pluginAdded = [];
  @Input() agentNode = '';
  selectedPlugins = [];
  public confirmSavePlugins: any = [];
  constructor(@Inject(NZ_DRAWER_DATA) public nzData: any) {}

  ngOnInit() {
    this.pluginAdded = this.nzData.pluginAdded;
    this.agentNode = this.nzData.agentNode;
    this.selectedPlugins = this.pluginAdded?.map((item: any) => {
      return {
        ...item,
        id: `${item.id}#${item?.tool_id ?? '0'}`,
      };
    });
  }
  public isDisabledPlugin() {
    return this.confirmSavePlugins.length > 20;
  }

  public handlePluginAdded(pluginAdded: any[]) {
    this.confirmSavePlugins = pluginAdded.map(item => {
      const [id, tool_id] = item.id.split('#');
      return {
        ...item,
        id,
        tool_id: tool_id ?? '0',
      };
    });
  }

  public handlePluginReduced(pluginReduced: any[]) {
    this.confirmSavePlugins = [...pluginReduced];
  }

  dismiss(): void {
    if (this.nzData.dismiss && typeof this.nzData.dismiss === 'function') {
      this.nzData.dismiss({
        reason: false,
      });
    }
  }

  close(): void {
    if (this.nzData.afterClose && typeof this.nzData.afterClose === 'function') {
      this.nzData.afterClose(this.confirmSavePlugins);
    }
  }
}
