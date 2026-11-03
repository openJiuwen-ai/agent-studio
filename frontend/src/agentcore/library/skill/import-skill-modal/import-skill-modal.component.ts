import { HttpClient } from '@angular/common/http';
import { Component, EventEmitter, inject, Input, Output } from '@angular/core';
import { AbstractControl, FormBuilder, FormControl, FormGroup, ValidationErrors } from '@angular/forms';
import { I18NEXT_NAMESPACE, I18NextModule } from 'angular-i18next';
import { Unzipped, unzipSync } from 'fflate';
import { lastValueFrom } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { SkillApi } from '@agentcore/api/skill.api';
import { I18N_NAMESPACE } from '@agentcore/constants/common';
import { IMPORT_TYPE } from '@agentcore/constants/skill';
import { i18nProviderValue, I18nService } from '@agentcore/core/i18n.service';
import { HelpDocKey } from '@constants/support-topic.const';
import { MODULES } from '@shared/modules';
import { HelpLinksService } from '@shared/services/help-links.service';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzUploadFile } from 'ng-zorro-antd/upload';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { cdnAssetUrl } from '../../../../single-spa/assets-url';
import { SkillInfo } from '../interface/skill.interface';
import { SkillCommonService } from '../services/skill.common.service';

@Component({
  selector: 'meta-import-skill',
  templateUrl: './import-skill-modal.component.html',
  styleUrls: ['./import-skill-modal.component.scss'],
  standalone: true,
  imports: [MODULES, I18NextModule, NzToolTipModule, NzButtonModule],
  providers: [
    I18nService,
    {
      provide: I18NEXT_NAMESPACE,
      useValue: i18nProviderValue([I18N_NAMESPACE.Common, I18N_NAMESPACE.Skill]),
    },
  ],
})
export class ImportSkillModalComponent {
  @Input() importType: string;
  @Output() importSuccess = new EventEmitter<string>();
  readonly modalRef = inject(NzModalRef);
  public obsForm: FormGroup;
  public selectedFile: NzUploadFile;
  public maxSize = 10 * 1024 * 1024;
  public uploadType = ['.zip'];
  public skillInfo: SkillInfo;
  public skillLink = '';
  public isShowResult = false;
  public importTypeEnum = IMPORT_TYPE;
  public importZipErrorTip = '';
  public obsfileData;
  public obsfileName = '';
  protected readonly changeUrl = cdnAssetUrl;
  public fileList: NzUploadFile[] = [];
  constructor(
    private http: HttpClient,
    fb: FormBuilder,
    private skillApi: SkillApi,
    private readonly i18n: I18nService,
    private helpLinksService: HelpLinksService,
    private skillCommonService: SkillCommonService,
    private message: NzMessageService
  ) {
    this.obsForm = fb.group({
      obsAddress: new FormControl('', [this.obsAddressValidator()]),
    });
  }

  get obsAddressValue() {
    return this.obsForm.controls?.obsAddress?.value;
  }

  get isButtonDisabled() {
    return !this.obsAddressValue || (this.obsAddressValue && this.isShowResult) || (this.obsAddressValue && !this.obsForm.valid);
  }

  ngOnInit(): void {
    this.skillLink = this.helpLinksService.getHelpCenterLink(HelpDocKey.MODELARTS_PRICES);
    this.obsForm.controls.obsAddress?.valueChanges.pipe(debounceTime(300), distinctUntilChanged()).subscribe(value => this.onObsAddressChange(value));
    this.skillCommonService.initObsEndpoint();
  }

  private obsAddressValidator() {
    const obsAddressReg = /^(https?:\/\/).+$/;
    return (control: AbstractControl): ValidationErrors | null =>
      obsAddressReg.test(control.value)
        ? null
        : {
            obsAddress: {
              tiErrorMessage: this.i18n.transform('skill.import.obs.input.valid.address'),
            },
          };
  }

  async onAddFileSuccess(fileItem: any) {
    this.importZipErrorTip = '';
    this.selectedFile = fileItem;
    const file = this.selectedFile as any;

    try {
      const arrayBuffer = await file.arrayBuffer();
      // 防竞态：await 期间用户可能点 × 移除或重选了别的文件，
      // 若 selectedFile 已不再指向本次解析的文件，则丢弃本次结果，避免把已移除文件的解析结果写回状态。
      if (this.selectedFile !== file) {
        return;
      }
      const unzipped = unzipSync(new Uint8Array(arrayBuffer));
      this.unZip(unzipped);
    } catch (error) {
      if (this.selectedFile !== file) {
        return;
      }
      this.importZipErrorTip = this.i18n.transform('skill.import.result.null');
      this.isShowResult = true;
    }
  }

  public onAddItemFailed(info: { validResults: string[] }) {
    const error_type = info.validResults[0];
    if (error_type === 'type') {
      this.message.error(this.i18n.transform('only_support_upload_format', { types: this.uploadType.join(',') }));
    }
    if (error_type === 'maxSize') {
      this.message.error(this.i18n.transform('file_size_cannot_exceed', { size: this.maxSize / (1024 * 1024) }));
    }
  }

  public confirm() {
    const formData = new FormData();
    if (this.importType === this.importTypeEnum.ZIP) {
      formData.append('file', this.selectedFile as any);
    } else {
      const blob = new Blob([this.obsfileData], { type: 'application/x-zip-compressed' });
      formData.append('file', blob, this.obsfileName);
    }

    this.skillApi.importSkill(formData).subscribe({
      next: res => {
        this.close();
        const msg =
          this.importType === IMPORT_TYPE.OBS
            ? this.i18n.transform('skill.import_obs_success_tip')
            : this.i18n.transform('skill.import_zip_success_tip', { name: (this.selectedFile as any)?.name });
        this.message.success(msg);
        this.importSuccess.emit();
        this.modalRef.destroy();
      },
    });
  }

  public onRemoveItems() {
    if (this.selectedFile) {
      this.selectedFile = undefined;
    }
    this.fileList = [];
    this.isShowResult = false;
    this.skillInfo = { name: '', description: '' };
  }

  public onObsAddressChange(value: string) {
    this.skillInfo = { name: '', description: '' };
    this.isShowResult = false;
  }

  public async downloadAndUnzip() {
    const url = this.obsForm.controls.obsAddress.value;
    try {
      const buffer = await lastValueFrom(this.http.get(url, { responseType: 'arraybuffer' }));
      this.obsfileName = url.split('?')?.[0]?.split('/')?.pop() || 'default.zip';
      this.obsfileData = new Blob([buffer], { type: 'application/zip' });

      if (buffer.byteLength > this.maxSize) {
        this.message.error(this.i18n.transform('file_size_cannot_exceed', { size: this.maxSize / (1024 * 1024) }));
        return;
      }
      const data: Unzipped = unzipSync(new Uint8Array(buffer));
      this.unZip(data);
    } catch (err) {
      this.message.error(this.i18n.transform('skill.import.result.unzipError'));
    }
  }

  dismiss(): void {
    this.modalRef.destroy();
  }

  close(): void {}

  private parseSkillMd(content: string): { name: string; description: string } {
    const skill = { name: '', description: '' };
    // 查找 frontmatter：起始 --- 在文件开头，结束 --- 必须在行首（前面是换行符）
    // 避免匹配 block scalar 内容中的缩进 ---
    if (!content.startsWith('---')) {
      return skill;
    }
    let endFront = -1;
    let searchFrom = 3;
    while (true) {
      const pos = content.indexOf('---', searchFrom);
      if (pos === -1) break;
      if (pos > 0 && content[pos - 1] === '\n') {
        endFront = pos;
        break;
      }
      searchFrom = pos + 3;
    }
    if (endFront === -1) return skill;
    const lines = content.substring(3, endFront).trim().split('\n');

    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) {
        i++;
        continue;
      }
      // 跳过缩进行（非顶层 key）
      if (line.charAt(0) === ' ' || line.charAt(0) === '\t') {
        i++;
        continue;
      }

      if (trimmed.startsWith('name:')) {
        skill.name = trimmed.slice(5).trim();
      } else if (trimmed.startsWith('description:')) {
        let value = trimmed.slice(12).trim();
        // YAML block scalar: | (literal) 或 > (folded)，支持 chomping indicator (- +)
        const isBlockScalar = value === '|' || value === '>' || value === '|-' || value === '|+' || value === '>-' || value === '>+';
        if (isBlockScalar) {
          const isFolded = value.startsWith('>');
          const blockLines: string[] = [];
          i++;
          let firstLine = true;
          let lastWasBlankLine = false;
          while (i < lines.length) {
            const bl = lines[i];
            // 去除行尾 \r 以兼容 Windows CRLF 换行
            const blTrimmed = bl.replace(/\r$/, '');
            // 空行属于 block 内容（段落分隔）
            if (blTrimmed.length === 0) {
              i++;
              if (blockLines.length > 0) {
                blockLines.push('\n');
              }
              lastWasBlankLine = true;
              continue;
            }
            // 缩进行属于 block scalar
            if (bl.charAt(0) === ' ' || bl.charAt(0) === '\t') {
              if (!firstLine && !lastWasBlankLine) {
                // folded 模式换行合并为空格，但空行后不再追加空格（YAML folded 语义）
                blockLines.push(isFolded ? ' ' : '\n');
              }
              blockLines.push(bl.trim());
              firstLine = false;
              lastWasBlankLine = false;
              i++;
            } else {
              break;
            }
          }
          skill.description = blockLines.join('').trim();
          continue;
        }
        skill.description = value;
      }
      i++;
    }
    return skill;
  }

  private unZip(unzipped) {
    const fileMap: Record<string, string> = {};
    for (const [originalPath, buffer] of Object.entries(unzipped)) {
      const content = new TextDecoder().decode(buffer as ArrayBuffer);
      const standardizedPath = this.normalizePath(originalPath);
      fileMap[standardizedPath] = content;
    }
    const rootFiles = Object.keys(fileMap);

    // isShowResult 语义：成功解析出 SKILL.md 且 frontmatter 含 name/description 时置 true；
    // 错误分支同样保持 true，但清空 skillInfo，以便模板 @else 分支渲染 importZipErrorTip
    // （importZipErrorTip 仅在 @if (isShowResult) 区块内渲染，见模板）。
    this.isShowResult = false;

    // 与后端 validateDirectoryStructure 的 equalsIgnoreCase 对齐：SKILL.md 判断大小写不敏感
    const SKILL_MD_LOWER = 'skill.md';
    const findSkillMdKey = (predicate: (path: string) => boolean) =>
      rootFiles.find(p => {
        const lower = p.toLowerCase();
        return predicate(lower);
      });

    // 策略1：根级 SKILL.md（平铺结构）
    // 与后端对齐：根级 SKILL.md 存在即进入平铺分支。但如果根级 SKILL.md 不带 frontmatter
    //（name/description 为空），且子目录有带 frontmatter 的 SKILL.md，则回落到策略2
    const rootSkillMdKey = findSkillMdKey(p => p === SKILL_MD_LOWER);
    if (rootSkillMdKey) {
      const rootParsed = this.parseSkillMd(fileMap[rootSkillMdKey]);
      const rootHasFrontmatter = rootParsed.name?.trim() && rootParsed.description?.trim();
      // 检查子目录是否有带 frontmatter 的 SKILL.md
      const nestedSkillMdKeys = rootFiles.filter(p => {
        const lower = p.toLowerCase();
        return lower !== SKILL_MD_LOWER && lower.endsWith('/' + SKILL_MD_LOWER);
      });
      const hasNestedWithFrontmatter = nestedSkillMdKeys.some(key => {
        const parsed = this.parseSkillMd(fileMap[key]);
        return parsed.name?.trim() && parsed.description?.trim();
      });

      if (rootHasFrontmatter) {
        // 根级带 frontmatter：禁止子目录再出现带 frontmatter 的 SKILL.md
        if (hasNestedWithFrontmatter) {
          this.skillInfo = { name: '', description: '' };
          this.importZipErrorTip = this.i18n.transform('skill.import.result.valid.tip1');
          this.isShowResult = true;
          return;
        }
        this.skillInfo = rootParsed;
        this.isShowResult = true;
        return;
      } else if (!hasNestedWithFrontmatter) {
        // 根级不带 frontmatter，子目录也没有带 frontmatter 的 SKILL.md
        // 仍按平铺处理，展示解析结果（空的 name/description → 报"解析结果为空"）
        this.skillInfo = rootParsed;
        if (!rootParsed.name?.trim() || !rootParsed.description?.trim()) {
          this.importZipErrorTip = this.i18n.transform('skill.import.result.null');
        }
        this.isShowResult = true;
        return;
      }
      // 根级不带 frontmatter 但子目录有带 frontmatter 的 → 回落到策略2
    }

    // 策略2：单文件夹结构 {folderName}/SKILL.md
    // 与后端情况2对齐：优先用带 frontmatter 的候选消歧；若全部不带 frontmatter，用全部候选
    // 这样单文件夹结构下 SKILL.md 缺字段时仍能选中并展示解析结果（空的 name/description → 报"解析结果为空"）
    const allCandidates = rootFiles.filter(p => p.toLowerCase().endsWith('/' + SKILL_MD_LOWER));
    const frontmatterCandidates = allCandidates.filter(key => {
      const parsed = this.parseSkillMd(fileMap[key]);
      return parsed.name?.trim() && parsed.description?.trim();
    });
    const skillMdCandidates = frontmatterCandidates.length > 0 ? frontmatterCandidates : allCandidates;
    if (skillMdCandidates.length !== 1) {
      this.skillInfo = { name: '', description: '' };
      this.importZipErrorTip = this.i18n.transform('skill.import.result.valid.tip1');
      this.isShowResult = true;
      return;
    }
    const skillMdPath = skillMdCandidates[0];
    const folderName = skillMdPath.slice(0, -('/' + SKILL_MD_LOWER).length);
    // SKILL.md 必须直接位于该子目录根级，不允许 a/b/SKILL.md（后端校验 {name}/SKILL.md 规范）
    if (folderName.includes('/')) {
      this.skillInfo = { name: '', description: '' };
      this.importZipErrorTip = this.i18n.transform('skill.import.result.valid.tip1');
      this.isShowResult = true;
      return;
    }
    // 根级非空目录唯一性：含 SKILL.md 的目录必须是根级唯一的非空目录（与后端情况2对齐）
    // 否则如 assets/ + my-skill/SKILL.md 会通过前端预览，但后端以 FILES_NUMBER_DOES_NOT_MATCH 拒绝
    const rootLevelDirs = new Set(
      rootFiles
        .filter(p => p.includes('/'))
        .map(p => p.split('/')[0])
    );
    for (const dir of rootLevelDirs) {
      if (dir !== folderName) {
        this.skillInfo = { name: '', description: '' };
        this.importZipErrorTip = this.i18n.transform('skill.import.result.valid.tip1');
        this.isShowResult = true;
        return;
      }
    }
    const parsed = this.parseSkillMd(fileMap[skillMdPath]);
    this.skillInfo = parsed;
    if (!parsed.name?.trim() || !parsed.description?.trim()) {
      this.importZipErrorTip = this.i18n.transform('skill.import.result.null');
    }
    this.isShowResult = true;
  }

  private normalizePath(rawPath: string): string {
    let normalized = rawPath.replace(/\\/g, '/');
    normalized = normalized.replace(/\/+/g, '/');
    normalized = normalized.replace(/\/+$/, '');
    return normalized;
  }

  handleUploadChange(fileItem: any): void {
    if (fileItem.type === 'removed') {
      this.onRemoveItems();
      return;
    }
    if (fileItem.type !== 'start') {
      return;
    }
    this.fileList = [fileItem.file];
    if (fileItem.file.name.lastIndexOf('.zip') < 0) {
      this.onAddItemFailed({ validResults: ['type'] });
      this.onRemoveItems();
      return;
    }
    this.onAddFileSuccess(fileItem.file.originFileObj);
  }
}
