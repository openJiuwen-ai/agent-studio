import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ConversationSkillItem } from '../conversation-skill.model';
import { SkillSelectorComponent } from './skill-selector.component';

@Component({
  standalone: true,
  imports: [SkillSelectorComponent],
  template: `
    <app-skill-selector
      [skills]="skills"
      [value]="value"
      [disabled]="disabled"
      (valueChange)="value = $event; valueChanges.push($event)"
      (selectedSkillsChange)="selectedChanges.push($event)"
      (sendRequested)="sendCount = sendCount + 1"
    />
  `,
})
class SkillSelectorHostComponent {
  skills: ConversationSkillItem[] = [];
  value = '';
  disabled = false;
  sendCount = 0;
  valueChanges: string[] = [];
  selectedChanges: ConversationSkillItem[][] = [];
}

@Component({
  standalone: true,
  imports: [SkillSelectorComponent],
  template: `
    <app-skill-selector [skills]="skills" [value]="firstValue" />
    <app-skill-selector [skills]="skills" [value]="secondValue" />
  `,
})
class MultipleSkillSelectorHostComponent {
  skills = [skill('s1', 'meeting-minutes')];
  firstValue = '/meet';
  secondValue = '/meet';
}

describe('SkillSelectorComponent', () => {
  let fixture: ComponentFixture<SkillSelectorHostComponent>;
  let host: SkillSelectorHostComponent;
  let component: SkillSelectorComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SkillSelectorHostComponent, MultipleSkillSelectorHostComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SkillSelectorHostComponent);
    host = fixture.componentInstance;
    component = fixture.debugElement.children[0].componentInstance;
    fixture.detectChanges();
  });

  it('通过 textarea 的 / 过滤和 Enter 选择，并删除触发片段', () => {
    host.skills = [skill('s1', 'meeting-minutes'), skill('s2', 'professional-rewriter')];
    fixture.detectChanges();
    inputText('请处理 /meet');

    expect(menuOptions().map((item) => item.id)).toEqual([component.optionId(0)]);
    expect(menuOptions()[0].textContent).toContain('meeting-minutes');

    keydown('Enter');
    fixture.detectChanges();

    expect(host.value).toBe('请处理 ');
    expect(chips().map((chip) => chip.textContent?.trim())).toEqual(['meeting-minutes×']);
    expect(host.selectedChanges.map((items) => items.map((item) => item.skillId))).toEqual([['s1']]);
  });

  it('在中文多行正文中部选择后保留后缀并恢复 textarea 焦点与光标', async () => {
    host.skills = [skill('s1', '会议')];
    fixture.detectChanges();
    const source = '第一行\n中文 /会后缀';
    const cursor = source.indexOf('后缀');

    inputText(source, cursor);
    click(menuOptions()[0]);
    fixture.detectChanges();
    await Promise.resolve();

    const textarea = input();
    expect(host.value).toBe('第一行\n中文 后缀');
    expect(textarea.selectionStart).toBe('第一行\n中文 '.length);
    expect(textarea.selectionEnd).toBe('第一行\n中文 '.length);
    expect(document.activeElement).toBe(textarea);
  });

  it('只在行首或空白边界识别斜杠，并允许多行触发', () => {
    host.skills = [skill('s1', 'meeting-minutes')];
    fixture.detectChanges();

    inputText('前缀/meet');
    expect(menu()).toBeNull();
    inputText('前缀 /meet');
    expect(menu()).not.toBeNull();
    inputText('前缀\n/meet');
    expect(menu()).not.toBeNull();
  });

  it('组合输入期间的 Enter 不选择、不发送、不删除正文', () => {
    host.skills = [skill('s1', '会议')];
    fixture.detectChanges();
    const textarea = input();

    textarea.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true, data: 'hui' }));
    textarea.value = '/会';
    textarea.setSelectionRange(2, 2);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
    const enter = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true });
    textarea.dispatchEvent(enter);
    fixture.detectChanges();

    expect(enter.defaultPrevented).toBeFalse();
    expect(host.value).toBe('/会');
    expect(component.selectedSkills).toEqual([]);
    expect(host.sendCount).toBe(0);
    expect(menu()).toBeNull();

    textarea.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true, data: '会' }));
    fixture.detectChanges();
    expect(menu()).not.toBeNull();
  });

  it('IME 在 compositionend 前的最终 input 只为同一真实值发射一次', () => {
    host.skills = [skill('s1', '会议')];
    fixture.detectChanges();
    const textarea = input();

    textarea.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }));
    textarea.value = '/会';
    textarea.setSelectionRange(2, 2);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
    fixture.detectChanges();

    expect(host.valueChanges).toEqual(['/会']);
    expect(menu()).not.toBeNull();
  });

  it('IME 在 compositionend 后的最终 input 只为同一真实值发射一次', () => {
    host.skills = [skill('s1', '会议')];
    fixture.detectChanges();
    const textarea = input();

    textarea.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }));
    textarea.value = '/会';
    textarea.setSelectionRange(2, 2);
    textarea.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true }));
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();

    expect(host.valueChanges).toEqual(['/会']);
    expect(menu()).not.toBeNull();
  });

  it('外部 value 更新立即关闭旧菜单，Enter 不会删除新正文', () => {
    host.skills = [skill('s1', 'a')];
    fixture.detectChanges();
    inputText('/a');
    expect(menu()).not.toBeNull();

    host.value = 'server';
    fixture.detectChanges();
    keydown('Enter');
    fixture.detectChanges();

    expect(menu()).toBeNull();
    expect(host.value).toBe('server');
    expect(component.selectedSkills).toEqual([]);
    expect(host.sendCount).toBe(1);
  });

  it('外部 disabled 更新立即关闭菜单并阻止菜单交互', () => {
    host.skills = [skill('s1', 'a')];
    fixture.detectChanges();
    inputText('/a');

    host.disabled = true;
    fixture.detectChanges();
    keydown('Enter');

    expect(input().disabled).toBeTrue();
    expect(input().getAttribute('aria-expanded')).toBe('false');
    expect(menu()).toBeNull();
    expect(component.selectedSkills).toEqual([]);
    expect(host.sendCount).toBe(0);
  });

  it('上下键循环、Esc 关闭、Shift+Enter 换行，普通 Enter 发送', () => {
    host.skills = [skill('s1', 'a'), skill('s2', 'b')];
    fixture.detectChanges();
    inputText('/');

    keydown('ArrowUp');
    expect(menuOptions()[1].getAttribute('aria-selected')).toBe('true');
    keydown('ArrowDown');
    expect(menuOptions()[0].getAttribute('aria-selected')).toBe('true');
    keydown('Escape');
    expect(menu()).toBeNull();

    const shiftEnter = keydown('Enter', { shiftKey: true });
    expect(shiftEnter.defaultPrevented).toBeFalse();
    expect(host.sendCount).toBe(0);
    const enter = keydown('Enter');
    expect(enter.defaultPrevented).toBeTrue();
    expect(host.sendCount).toBe(1);
  });

  it('菜单 click 多选去重保序，chip click 只删除对应推荐', () => {
    host.skills = [skill('s1', 'a'), skill('s2', 'b')];
    fixture.detectChanges();

    inputText('/a');
    click(menuOptions()[0]);
    fixture.detectChanges();
    inputText('/b');
    click(menuOptions()[0]);
    fixture.detectChanges();
    inputText('/b');
    click(menuOptions()[0]);
    fixture.detectChanges();

    expect(component.selectedSkills.map((item) => item.skillId)).toEqual(['s1', 's2']);
    expect(host.selectedChanges.map((items) => items.map((item) => item.skillId))).toEqual([['s1'], ['s1', 's2']]);
    click(chips()[0].querySelector('button')!);
    fixture.detectChanges();
    expect(component.selectedSkills.map((item) => item.skillId)).toEqual(['s2']);
    expect(host.value).toBe('');
  });

  it('目录更新删除失效项、替换为 canonical 对象且只按真实变化发射一次', () => {
    const original = skill('s1', 'old');
    const updated = skill('s1', 'updated');
    host.skills = [original, skill('s2', 'second')];
    fixture.detectChanges();
    inputText('/old');
    click(menuOptions()[0]);
    fixture.detectChanges();
    expect(host.selectedChanges.length).toBe(1);

    host.skills = [updated, updated, skill('s2', 'second')];
    fixture.detectChanges();
    expect(component.selectedSkills).toEqual([updated]);
    expect(component.selectedSkills[0]).toBe(updated);
    expect(host.selectedChanges.length).toBe(2);

    host.skills = [updated, skill('s2', 'second')];
    fixture.detectChanges();
    expect(host.selectedChanges.length).toBe(2);

    host.skills = [];
    fixture.detectChanges();
    expect(component.selectedSkills).toEqual([]);
    expect(host.selectedChanges.length).toBe(3);
  });

  it('空目录和无匹配时保持稳定并允许发送', () => {
    inputText('/missing');
    expect(menu()).not.toBeNull();
    expect(menuOptions()).toEqual([]);
    expect(menu()!.textContent).toContain('没有匹配的技能');
    keydown('Enter');
    expect(host.sendCount).toBe(1);
  });

  it('命令式 setSkills 和 clearRecommendations 在 OnPush 组件中标记模板更新', () => {
    inputText('/');
    expect(menuOptions()).toEqual([]);

    component.setSkills([skill('s1', 'meeting-minutes')]);
    fixture.detectChanges();
    expect(menuOptions().map((option) => option.textContent?.trim())).toEqual(['meeting-minutesdescription-meeting-minutes']);

    click(menuOptions()[0]);
    fixture.detectChanges();
    expect(chips().length).toBe(1);
    component.clearRecommendations();
    fixture.detectChanges();
    expect(chips()).toEqual([]);
  });

  it('每个实例使用唯一且稳定的 menu 与 option ID，并保持 ARIA 关联', () => {
    const multipleFixture = TestBed.createComponent(MultipleSkillSelectorHostComponent);
    multipleFixture.detectChanges();
    const textareas = Array.from(multipleFixture.nativeElement.querySelectorAll('textarea')) as HTMLTextAreaElement[];
    textareas.forEach((textarea) => {
      textarea.value = '/meet';
      textarea.setSelectionRange(5, 5);
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    multipleFixture.detectChanges();

    const menus = Array.from(multipleFixture.nativeElement.querySelectorAll('[role="listbox"]')) as HTMLElement[];
    expect(new Set(menus.map((item) => item.id)).size).toBe(2);
    textareas.forEach((textarea, index) => {
      const option = menus[index].querySelector('[role="option"]') as HTMLElement;
      expect(textarea.getAttribute('aria-controls')).toBe(menus[index].id);
      expect(textarea.getAttribute('aria-activedescendant')).toBe(option.id);
    });
  });

  function input(): HTMLTextAreaElement {
    return fixture.nativeElement.querySelector('textarea') as HTMLTextAreaElement;
  }

  function inputText(value: string, cursor = value.length): void {
    const textarea = input();
    textarea.value = value;
    textarea.setSelectionRange(cursor, cursor);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    fixture.detectChanges();
  }

  function keydown(key: string, init: KeyboardEventInit = {}): KeyboardEvent {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
    input().dispatchEvent(event);
    fixture.detectChanges();
    return event;
  }

  function menu(): HTMLElement | null {
    return fixture.nativeElement.querySelector('[role="listbox"]') as HTMLElement | null;
  }

  function menuOptions(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('[role="option"]')) as HTMLElement[];
  }

  function chips(): HTMLElement[] {
    return Array.from(fixture.nativeElement.querySelectorAll('.skill-chip')) as HTMLElement[];
  }

  function click(element: Element): void {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  }
});

function skill(skillId: string, name: string): ConversationSkillItem {
  return { skillId, name, description: `description-${name}` };
}
