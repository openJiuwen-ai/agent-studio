import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  Output,
  ViewChild,
} from '@angular/core';
import { COMMON_MODULES, LIB_MODULES } from '@shared/modules';
import { ConversationSkillItem } from '../conversation-skill.model';

interface SlashTrigger {
  start: number;
  end: number;
  keyword: string;
}

@Component({
  selector: 'app-skill-selector',
  standalone: true,
  imports: [COMMON_MODULES, LIB_MODULES],
  templateUrl: './skill-selector.component.html',
  styleUrl: './skill-selector.component.less',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SkillSelectorComponent {
  private static nextInstanceId = 0;
  readonly menuId = `conversation-skill-selector-menu-${++SkillSelectorComponent.nextInstanceId}`;
  private catalogSkills: ConversationSkillItem[] = [];
  private activeTrigger: SlashTrigger | null = null;
  private inputValue = '';
  private inputDisabled = false;
  private composing = false;

  @ViewChild('textarea') private textarea?: ElementRef<HTMLTextAreaElement>;

  constructor(private readonly cdr: ChangeDetectorRef) {}

  @Input()
  set skills(items: ConversationSkillItem[]) {
    this.setSkills(items ?? []);
  }

  get skills(): ConversationSkillItem[] {
    return this.catalogSkills;
  }

  @Input()
  set disabled(value: boolean) {
    this.inputDisabled = value;
    if (value) {
      this.closeMenu();
      return;
    }
    this.cdr.markForCheck();
  }

  get disabled(): boolean {
    return this.inputDisabled;
  }

  @Input()
  set value(value: string) {
    const nextValue = value ?? '';
    if (nextValue === this.inputValue) {
      return;
    }
    this.inputValue = nextValue;
    this.closeMenu();
  }

  get value(): string {
    return this.inputValue;
  }

  @Output() readonly valueChange = new EventEmitter<string>();
  @Output() readonly selectedSkillsChange = new EventEmitter<ConversationSkillItem[]>();
  @Output() readonly sendRequested = new EventEmitter<void>();

  selectedSkills: ConversationSkillItem[] = [];
  filteredSkills: ConversationSkillItem[] = [];
  menuOpen = false;
  activeSkillIndex = -1;

  /** 清空本轮菜单确认过的推荐，不修改输入正文。 */
  public clearRecommendations(): void {
    if (!this.selectedSkills.length) {
      return;
    }
    this.selectedSkills = [];
    this.selectedSkillsChange.emit([]);
    this.cdr.markForCheck();
  }

  /** 使用目录原有顺序更新候选项，并按 Skill ID 去重。 */
  public setSkills(items: ConversationSkillItem[]): void {
    const seenIds = new Set<string>();
    this.catalogSkills = items.filter((item) => {
      if (seenIds.has(item.skillId)) {
        return false;
      }
      seenIds.add(item.skillId);
      return true;
    });
    const canonicalById = new Map(this.catalogSkills.map((item) => [item.skillId, item]));
    const canonicalSelected = this.selectedSkills
      .map((item) => canonicalById.get(item.skillId))
      .filter((item): item is ConversationSkillItem => Boolean(item));
    if (!this.sameSkillReferences(this.selectedSkills, canonicalSelected)) {
      this.selectedSkills = canonicalSelected;
      this.selectedSkillsChange.emit(this.selectedSkills);
    }
    this.refreshMenu();
  }

  public onTextareaInput(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    if (this.composing) {
      this.updateValue(textarea.value);
      this.closeMenu();
      return;
    }
    this.onValueInput(textarea.value, textarea.selectionStart ?? textarea.value.length);
  }

  public onCompositionStart(): void {
    this.composing = true;
    this.closeMenu();
  }

  public onCompositionEnd(event: CompositionEvent): void {
    this.composing = false;
    this.onTextareaInput(event);
  }

  /**
   * 更新输入文字，并仅识别光标前最后一个由行首或空白引导的 /关键词 片段。
   */
  public onValueInput(value: string, cursorPosition = value.length): void {
    if (this.disabled) {
      return;
    }

    this.updateValue(value);
    this.activeTrigger = this.findSlashTrigger(value, cursorPosition);
    this.refreshMenu();
  }

  public onKeydown(event: KeyboardEvent): void {
    if (this.disabled || this.composing || event.isComposing || event.keyCode === 229 || (event.shiftKey && event.key === 'Enter')) {
      return;
    }

    if (event.key === 'Escape' && this.menuOpen) {
      event.preventDefault();
      this.closeMenu();
      return;
    }

    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && this.menuOpen) {
      if (!this.filteredSkills.length) {
        return;
      }
      event.preventDefault();
      const offset = event.key === 'ArrowDown' ? 1 : -1;
      this.activeSkillIndex = (this.activeSkillIndex + offset + this.filteredSkills.length) % this.filteredSkills.length;
      this.cdr.markForCheck();
      return;
    }

    if (event.key !== 'Enter') {
      return;
    }

    event.preventDefault();
    if (this.menuOpen && this.filteredSkills.length) {
      this.selectSkill(this.filteredSkills[this.activeSkillIndex]);
      return;
    }
    this.sendRequested.emit();
  }

  /** 仅通过菜单调用；手写 /文本 不会调用此方法。 */
  public selectSkill(item: ConversationSkillItem): void {
    if (this.disabled) {
      return;
    }

    const selectedItem = this.catalogSkills.find((candidate) => candidate.skillId === item.skillId);
    const trigger = this.currentTrigger();
    if (!selectedItem || !trigger) {
      this.closeMenu();
      return;
    }

    if (!this.selectedSkills.some((selected) => selected.skillId === selectedItem.skillId)) {
      this.selectedSkills = [...this.selectedSkills, selectedItem];
      this.selectedSkillsChange.emit(this.selectedSkills);
    }

    const nextValue = this.value.slice(0, trigger.start) + this.value.slice(trigger.end);
    this.updateValue(nextValue);
    this.closeMenu();
    this.restoreTextareaFocus(trigger.start);
  }

  public removeSkill(skillId: string): void {
    if (this.disabled) {
      return;
    }
    const nextSelectedSkills = this.selectedSkills.filter((item) => item.skillId !== skillId);
    if (nextSelectedSkills.length === this.selectedSkills.length) {
      return;
    }
    this.selectedSkills = nextSelectedSkills;
    this.selectedSkillsChange.emit(this.selectedSkills);
    this.cdr.markForCheck();
  }

  public closeMenu(): void {
    this.menuOpen = false;
    this.activeSkillIndex = -1;
    this.activeTrigger = null;
    this.cdr.markForCheck();
  }

  public optionId(index: number): string {
    return `${this.menuId}-option-${index}`;
  }

  private refreshMenu(): void {
    if (!this.activeTrigger || this.disabled) {
      this.menuOpen = false;
      this.filteredSkills = [];
      this.activeSkillIndex = -1;
      this.cdr.markForCheck();
      return;
    }

    const keyword = this.activeTrigger.keyword.toLocaleLowerCase();
    this.filteredSkills = this.catalogSkills.filter((item) =>
      item.name.toLocaleLowerCase().includes(keyword) ||
      item.description.toLocaleLowerCase().includes(keyword),
    );
    this.menuOpen = true;
    this.activeSkillIndex = this.filteredSkills.length ? 0 : -1;
    this.cdr.markForCheck();
  }

  private findSlashTrigger(value: string, cursorPosition: number): SlashTrigger | null {
    const safeCursorPosition = Math.min(Math.max(cursorPosition, 0), value.length);
    const beforeCursor = value.slice(0, safeCursorPosition);
    const match = /(^|\s)\/([^\s\/]*)$/.exec(beforeCursor);
    if (!match) {
      return null;
    }
    const start = match.index + match[1].length;
    return { start, end: safeCursorPosition, keyword: match[2] };
  }

  private currentTrigger(): SlashTrigger | null {
    if (!this.activeTrigger) {
      return null;
    }
    const current = this.findSlashTrigger(this.value, this.activeTrigger.end);
    if (!current || current.start !== this.activeTrigger.start || current.end !== this.activeTrigger.end || current.keyword !== this.activeTrigger.keyword) {
      return null;
    }
    return current;
  }

  private updateValue(value: string): void {
    if (this.inputValue === value) {
      return;
    }
    this.inputValue = value;
    this.valueChange.emit(value);
    this.cdr.markForCheck();
  }

  private restoreTextareaFocus(position: number): void {
    queueMicrotask(() => {
      const textarea = this.textarea?.nativeElement;
      if (!textarea || this.disabled) {
        return;
      }
      textarea.focus();
      textarea.setSelectionRange(position, position);
    });
  }

  private sameSkillReferences(left: ConversationSkillItem[], right: ConversationSkillItem[]): boolean {
    return left.length === right.length && left.every((item, index) => item === right[index]);
  }
}
