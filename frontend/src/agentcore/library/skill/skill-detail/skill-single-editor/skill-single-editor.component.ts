import { CommonModule } from '@angular/common';
import { Component, effect, ElementRef, HostListener, input, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { MarkdownComponent, MarkdownService, MarkedOptions, MarkedRenderer } from 'ngx-markdown';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { CustomTreeNode, SkillEditorTab } from '@agentcore/constants/skill.model';
import { I18nService } from '@agentcore/core/i18n.service';
import { CustomFileTreeComponent } from '@agentcore/shared/components/custom-editor/custom-file-tree/custom-file-tree.component';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { CustomEditorService } from '@agentcore/shared/services/custom-editor.service';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { CustomEditorIconComponent } from '@agentcore/shared/components/custom-editor/custom-editor-icon/custom-editor-icon.component';

class TreeUtil {
  static expandNode(data: CustomTreeNode[], node: CustomTreeNode): void {
    node.expanded = true;
  }

  static selectNode(data: CustomTreeNode[], node: CustomTreeNode, emit: boolean): void {
    node.selected = true;
  }
}

@Component({
  selector: 'skill-single-editor',
  templateUrl: './skill-single-editor.html',
  styleUrls: ['./skill-single-editor.component.scss'],
  standalone: true,
  imports: [
    NzSpinModule,
    NzTabsModule,
    NzIconModule,
    FormsModule,
    CommonModule,
    MonacoEditorModule,
    CustomEditorIconComponent,
    MarkdownComponent,
    CustomFileTreeComponent,
    I18nPipe,
    NzRadioModule,
  ],
  providers: [CustomEditorService, I18nService],
})
export class SkillSingleEditorComponent {
  @ViewChild('container') containerRef!: ElementRef;
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  radioValue = SkillEditorTab.MD;
  tabs: Array<any> = [
    {
      iconName: 'md-icon',
      id: SkillEditorTab.MD,
      active: false,
      disabled: true,
      tip: this._i18n.transform('skill.detail.codeEditor.mdTab.tip'),
    },
    {
      id: SkillEditorTab.CODE,
      active: false,
      iconName: 'code-icon',
      disabled: true,
      tip: this._i18n.transform('skill.detail.codeEditor.codeTab.tip'),
    },
  ];
  editorOptions: any = {
    theme: 'vs',
    lineNumbers: 'on',
    lineNumbersMinChars: 3,
    lineDecorationsWidth: 3,
    automaticLayout: true,
    readOnly: true,
  };
  selectedFileData: CustomTreeNode | undefined;
  selectedTab = '';
  innerData: Array<CustomTreeNode> = [];
  code = '';
  markdownContent = '';
  editorTip = '';
  fileTreeWidth = 330;
  isResizing = false;
  skillEditorTab = SkillEditorTab;
  loading = false;
  skillIdInput = input.required<string>();

  readonly myMarkedOptions: MarkedOptions = {
    renderer: (() => {
      const renderer = new MarkedRenderer();
      renderer.heading = (text: string, level: number) => {
        // 关键：去掉 HTML 标签，直接取纯文本作为 ID
        // 这样目录中的 [#翻译原则] 就能准确匹配到 id="翻译原则"
        const id = text.replace(/<[^>]*>/g, '').trim();
        return `<h${level} id="${id}">${text}</h${level}>`;
      };
      return renderer;
    })(),
    gfm: true,
    breaks: true,
  };

  constructor(
    private markdownService: MarkdownService,
    private _i18n: I18nService,
    private _customEditorService: CustomEditorService
  ) {
    effect(() => {
      const skillId = this.skillIdInput();
      if (skillId) {
        this.resetData();
        this.loadPackage(skillId);
      }
    });
    this.setupMarkdownRenderer();
  }

  resetData() {
    this.selectedFileData = undefined;
    this.unsetAllTab();
    this.innerData = [];
    this.code = '';
    this.markdownContent = '';
    this.editorTip = '';
  }

  @HostListener('window:mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    if (!this.isResizing) {
      return;
    }

    // 使用动画帧确保拖动跟手且不掉帧
    window.requestAnimationFrame(() => {
      const container = this.containerRef.nativeElement;
      const rect = container.getBoundingClientRect();

      const containerLeft = rect.left;
      const containerWidth = rect.width;

      // 1. 计算鼠标相对于容器的理论偏移量
      let newWidth = event.clientX - containerLeft;

      // 2. 边界限制
      // 下限：防止负数
      if (newWidth < 0) {
        newWidth = 0;
      }

      // 上限：不能超过容器总宽度（减去 50px 预留给编辑器）
      const maxWidth = containerWidth;
      if (newWidth > maxWidth) {
        newWidth = maxWidth;
      }

      this.fileTreeWidth = newWidth;
    });
  }

  @HostListener('window:mouseup')
  onMouseUp() {
    if (this.isResizing) {
      this.isResizing = false;
      document.body.style.cursor = 'default';
    }
  }

  setupMarkdownRenderer() {
    // 设置标题 ID 的生成规则，确保能匹配你的中文目录
    this.markdownService.renderer.heading = (text: string, level: number) => {
      const id = text.trim();
      return `<h${level} id="${id}">${text}</h${level}>`;
    };
  }

  // 之前的点击拦截逻辑保持不变
  handlePreviewClick(event: MouseEvent) {
    const anchor = (event.target as HTMLElement).closest('a');
    if (!anchor) {
      return;
    }

    const href = anchor.getAttribute('href');
    if (!href) {
      return;
    }

    // 逻辑 A：锚点跳转 (以 # 开头)
    if (href.startsWith('#')) {
      event.preventDefault();
      const targetId = decodeURIComponent(href.substring(1));
      const element = document.getElementById(targetId);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    } else if (href.endsWith('.md') && !href.startsWith('http')) {
      event.preventDefault();

      // 这里的 href 就是 "references/terminology-guide.md"
      // 我们通知父组件或服务去加载这个新文件
      this.onFileJump(href);
    }
  }

  /**
   * 根据当前节点和相对路径找到目标节点
   * @param {Object} tree - 整个文件树的根节点 (multi-language-translation)
   * @param {string} currentNodePath - 当前选中节点的绝对路径 (例如: "references/guide.md")
   * @param {string} targetRelativePath - 目标的相对路径 (例如: "../assets/img.png")
   * @returns {Object|null} 目标节点对象
   */
  findNodeByContext(tree: CustomTreeNode, currentNodePath: string, targetRelativePath: string): CustomTreeNode | null {
    // 1. 获取当前目录路径
    let segments = currentNodePath.split('/').filter(Boolean);
    segments.pop(); // 移除文件名，剩下目录路径
    // 2. 处理相对路径
    if (targetRelativePath.startsWith('/')) {
      segments = [];
    }

    const relParts = targetRelativePath.split('/').filter(Boolean);
    for (const part of relParts) {
      if (part === '..') {
        segments.pop();
      } else if (part !== '.') {
        segments.push(part);
      }
    }

    // --- 关键修复开始 ---

    // 如果路径的第一段是根节点的 label，必须删掉它
    // 因为查找是从根节点的子级（tree.children）开始的
    if (segments.length > 0 && segments[0] === tree.label) {
      segments.shift();
    }

    // 如果处理完后 segments 为空，且原本就是要找根节点
    if (segments.length === 0) {
      return tree;
    }

    // --- 关键修复结束 ---

    // 3. 顺着 children 找
    let curr: CustomTreeNode | undefined = tree;
    for (const label of segments) {
      if (!curr || !curr.children) {
        return null;
      }

      // 在当前节点的子节点中找匹配的 label
      curr = curr.children.find(child => child.label === label);

      if (!curr) {
        return null;
      }
    }

    return curr;
  }

  onFileJump(path: string) {
    const pathNode = this.findNodeByContext(this.innerData[0], this.selectedFileData.path, path);
    if (pathNode) {
      this.onNodeSelect(pathNode);
    }
  }

  openSkillMd() {
    if (!this.innerData[0]) {
      // 文件树为空（如下载失败或 zip 解压异常），避免后续访问 .path 抛 TypeError
      return;
    }
    const skillMd = this.findNodeByContext(this.innerData[0], this.selectedFileData?.path ?? '', `${this.innerData[0].path}/SKILL.md`);
    if (skillMd) {
      this.onNodeSelect(skillMd);
    }
  }

  changeTree(tree: CustomTreeNode[], node: CustomTreeNode, isSelect, isExpand) {
    let res = null;
    res = (tree || []).map(item => {
      if (item.path === node.path) {
        item.selected = !!isSelect;
        if (isExpand) {
          item.expanded = true;
        } else {
          item.expanded = false;
        }
      } else {
        item.selected = !isSelect;
      }

      if (item.children && item.children.length > 0) {
        item.children = this.changeTree(item.children, node, isSelect, isExpand);
        item.isLeaf = false;
      } else {
        item.isLeaf = true;
      }
      return item;
    });
    return res;
  }

  async loadPackage(skillId: string) {
    this.loading = true;
    const fileTreeData = await this._customEditorService.downloadAndUnzipBySkillId(skillId);
    this.loading = false;
    if (fileTreeData[0]) {
      fileTreeData[0].expanded = true;
    }
    this.innerData = fileTreeData;
    this.openSkillMd();
  }

  setEditorSelected(language: string, event: CustomTreeNode) {
    const decoder = new TextDecoder('utf-8');
    this.editorOptions = { ...this.editorOptions, language };
    this.code = decoder.decode(event.content);
    if (language === 'markdown') {
      this.markdownContent = this.code;
      this.tabs.forEach(e => {
        e.active = e.id === SkillEditorTab.MD;
        e.disabled = false;
      });
      this.tabs = [...this.tabs];
      this.selectedTab = SkillEditorTab.MD;
      const element = this.scrollContainer?.nativeElement;
      if (element) {
        element.scrollTop = 0;
      }
    } else {
      this.tabs.forEach(e => {
        e.active = e.id === SkillEditorTab.CODE;
        e.disabled = true;
        if (e.id === SkillEditorTab.CODE) {
          e.disabled = false;
        }
      });
      this.tabs = [...this.tabs];
      this.selectedTab = SkillEditorTab.CODE;
    }
  }

  unsetAllTab() {
    this.selectedTab = '';
    this.tabs.forEach(e => {
      e.active = false;
      e.disabled = true;
    });
    this.tabs = [...this.tabs];
  }

  onNodeSelect(event: CustomTreeNode): void {
    if (event.isDir) {
      this.innerData = this.changeTree(this.innerData, event, true, !event.expanded);
    } else {
      this.innerData = this.changeTree(this.innerData, event, true, true);
      const { language } = event;
      this.selectedFileData = event;
      if (language) {
        this.setEditorSelected(language, event);
        this.editorTip = '';
      } else {
        this.selectedTab = '';
        this.tabs.forEach(e => {
          e.active = true;
          e.disabled = true;
        });
        this.tabs = [...this.tabs];
        this.editorTip = this._i18n.transform('skill.detail.editor.file.notSupportTip');
      }
    }
  }

  startResizing(event: MouseEvent) {
    this.isResizing = true;
    event.preventDefault();
    document.body.style.cursor = 'col-resize';
  }
}
