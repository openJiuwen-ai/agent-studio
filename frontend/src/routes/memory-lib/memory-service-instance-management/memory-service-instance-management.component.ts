import { ChangeDetectionStrategy, Component, computed, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { MemoryServiceInstanceApiService } from '@routes/memory-lib/memory-service-instance-api.service';
import { IMemoryServiceInstanceItem } from '@routes/memory-lib/memory-service-instance-interfaces';
import { ContextService } from '@services/context.service';
import { MemoryServiceInstanceModalComponent } from '@routes/memory-lib/memory-service-instance-management/memory-service-instance-modal/memory-service-instance-modal.component';
import { PipesModule } from '../../../pipes/pipes.module';

@Component({
  selector: 'memory-service-instance-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    I18NextModule,
    PipesModule,
    NzTableModule,
    NzButtonModule,
    NzInputModule,
    NzIconModule,
    NzBadgeModule,
    NzEmptyModule,
    NzSpinModule,
    NzDropDownModule,
    NzTypographyModule,
    NzToolTipModule,
    MemoryServiceInstanceModalComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MEMORY_LIB, I18nNamespace.COMMON],
    },
  ],
  templateUrl: './memory-service-instance-management.component.html',
  styleUrl: './memory-service-instance-management.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MemoryServiceInstanceManagementComponent implements OnInit {
  readonly instanceApiService = inject(MemoryServiceInstanceApiService);
  readonly ctxServ = inject(ContextService);
  readonly i18n = inject(I18NextEagerPipe);
  readonly message = inject(NzMessageService);
  readonly modal = inject(NzModalService);

  instances = signal<IMemoryServiceInstanceItem[]>([]);
  loading = signal(false);
  searchText = signal('');
  modalVisible = signal(false);
  editingInstanceId = signal<string>('');

  filteredInstances = computed(() => {
    const text = this.searchText().trim().toLowerCase();
    if (!text) {
      return this.instances();
    }
    return this.instances().filter(
      item =>
        item.name.toLowerCase().includes(text) ||
        item.base_url.toLowerCase().includes(text),
    );
  });

  ngOnInit() {
    this.queryInstances();
  }

  queryInstances() {
    this.loading.set(true);
    const workspaceId = this.ctxServ.currentWorkspaceId ?? '';
    this.instanceApiService
      .listInstances(workspaceId)
      .then(res => {
        this.instances.set(res.items ?? []);
      })
      .catch(() => {
        this.instances.set([]);
      })
      .finally(() => {
        this.loading.set(false);
      });
  }

  createInstance() {
    this.editingInstanceId.set('');
    this.modalVisible.set(true);
  }

  editInstance(instance: IMemoryServiceInstanceItem) {
    this.editingInstanceId.set(instance.instance_id);
    this.modalVisible.set(true);
  }

  deleteInstance(instance: IMemoryServiceInstanceItem) {
    this.modal.confirm({
      nzTitle: this.i18n.transform('memory.instance.delete.confirmTitle'),
      nzContent: this.i18n.transform('memory.instance.delete.confirmContent', { name: instance.name }),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzOkDanger: true,
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        const workspaceId = this.ctxServ.currentWorkspaceId ?? '';
        return this.instanceApiService
          .deleteInstance(workspaceId, instance.instance_id)
          .then(() => {
            this.message.success(this.i18n.transform('delete_success'));
            this.queryInstances();
          })
          .catch(() => {
            this.message.error(this.i18n.transform('delete_failed'));
          });
      },
    });
  }

  healthCheck(instance: IMemoryServiceInstanceItem) {
    const workspaceId = this.ctxServ.currentWorkspaceId ?? '';
    this.instanceApiService
      .healthCheck(workspaceId, instance.instance_id)
      .then(() => {
        this.queryInstances();
      })
      .catch(() => {
        this.queryInstances();
      });
  }

  onModalSaved() {
    this.modalVisible.set(false);
    this.queryInstances();
  }

  getHealthText(status: string): string {
    switch (status) {
      case 'HEALTHY':
        return this.i18n.transform('memory.instance.health.healthy');
      case 'UNHEALTHY':
        return this.i18n.transform('memory.instance.health.unhealthy');
      default:
        return this.i18n.transform('memory.instance.health.unknown');
    }
  }
}
