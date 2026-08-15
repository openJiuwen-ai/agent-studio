import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { I18NextModule, I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';

export interface ISearchFieldOption {
  label: string;
  id: string;
}

export interface ISearchField {
  label: string;
  field: string;
  options?: ISearchFieldOption[];
}

export interface ISearchTag {
  field: string;
  value: string;
  id?: string;
  label: string;
}

@Component({
  selector: 'multi-field-search',
  templateUrl: './multi-field-search.component.html',
  styleUrls: ['./multi-field-search.component.less'],
  standalone: true,
  imports: [CommonModule, FormsModule, NzSelectModule, NzTagModule, NzIconModule, NzToolTipModule, I18NextModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER]
    }
  ]
})
export class MultiFieldSearchComponent {
  @Input() searchItems: ISearchField[] = [];
  @Input() searchTags: ISearchTag[] = [];
  @Input() searchField: string = 'name';
  @Input() width: string = '100%';
  @Output() searchTagsChange = new EventEmitter<ISearchTag[]>();
  @Output() searchFieldChange = new EventEmitter<string>();
  @Output() searchChange = new EventEmitter<ISearchTag[]>();

  public searchInputValue: string = '';

  public get currentFieldHasOptions(): boolean {
    const item = this.searchItems.find(i => i.field === this.searchField);
    return !!item?.options?.length;
  }

  public get currentFieldOptions(): ISearchFieldOption[] {
    const item = this.searchItems.find(i => i.field === this.searchField);
    return item?.options || [];
  }

  public get selectedOptionLabel(): string {
    if (!this.searchInputValue) return '';
    const opt = this.currentFieldOptions.find(o => o.id === this.searchInputValue);
    return opt?.label || '';
  }

  public addSearchTag() {
    const item = this.searchItems.find(i => i.field === this.searchField);
    if (!item || !this.searchInputValue?.trim()) return;
    const existing = this.searchTags.find(t => t.field === this.searchField);
    if (existing) {
      existing.value = this.searchInputValue.trim();
    } else {
      this.searchTags = [...this.searchTags, { field: this.searchField, value: this.searchInputValue.trim(), label: item.label }];
    }
    this.searchInputValue = '';
    this.emitChange();
  }

  public addSearchTagFromOption(optionId: string) {
    const item = this.searchItems.find(i => i.field === this.searchField);
    if (!item || !optionId) return;
    const opt = item.options?.find(o => o.id === optionId);
    if (!opt) return;
    const existing = this.searchTags.find(t => t.field === this.searchField);
    // 取消选择：再次点击已选中项 → 移除标签并清空下拉框，搜索框不再显示该项
    if (existing && existing.id === optionId) {
      this.searchTags = this.searchTags.filter(t => t !== existing);
      this.searchInputValue = '';
      this.emitChange();
      return;
    }
    if (existing) {
      existing.value = opt.label;
      existing.id = opt.id;
    } else {
      this.searchTags = [...this.searchTags, { field: this.searchField, value: opt.label, id: opt.id, label: item.label }];
    }
    // 保留下拉框显示当前选中项，便于用户直观看到已选内容
    this.searchInputValue = optionId;
    this.emitChange();
  }

  public removeSearchTag(tag: ISearchTag) {
    this.searchTags = this.searchTags.filter(t => t !== tag);
    // 移除当前激活字段的标签时，同步清空下拉框显示
    if (tag.field === this.searchField) {
      this.searchInputValue = '';
    }
    this.emitChange();
  }

  public clearSearch() {
    this.searchTags = [];
    this.searchInputValue = '';
    // 保持当前选中的筛选字段不变，仅清空筛选条件；避免从"标签"清空后跳回"行业"
    this.emitChange();
  }

  public onSearchFieldChange(field: string) {
    this.searchField = field;
    // 切换到选项类字段时，恢复该字段已选中的项，使下拉框与已有标签保持一致
    const item = this.searchItems.find(i => i.field === field);
    if (item?.options?.length) {
      const existing = this.searchTags.find(t => t.field === field);
      this.searchInputValue = existing?.id || '';
    } else {
      this.searchInputValue = '';
    }
    this.searchFieldChange.emit(field);
  }

  private emitChange() {
    this.searchTagsChange.emit(this.searchTags);
    this.searchChange.emit(this.searchTags);
  }
}
