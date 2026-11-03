import {
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { MODULES } from '@shared/modules';
import { isNil } from 'lodash';
import { Subject, takeUntil } from 'rxjs';
import { NodeService } from '../../node.service';
import type { IWFView, IWFViewWithMultiType } from '../../node.type';
import { SetDefaultTipComponent } from '../set-default-tip/set-default-tip.component';
import { NzPopoverModule } from 'ng-zorro-antd/popover';
import { NzIconModule } from 'ng-zorro-antd/icon';

@Component({
  selector: 'meta-set-default',
  templateUrl: './set-default.component.html',
  styleUrls: ['./set-default.component.less'],
  standalone: true,
  imports: [MODULES, NzPopoverModule, NzIconModule, SetDefaultTipComponent],
})
export class SetDefaultComponent implements OnInit, OnDestroy {
  @Input() param: IWFViewWithMultiType | IWFView;

  @Input() isShowDesc: boolean;

  @Input() cmpWidth: string = '';

  @Input() host: string = 'default';
  @Output('changeParam') changeParam = new EventEmitter<any>();

  @ViewChild('setDefaultTipRef')
  setDefaultTipRef: any;

  public destroy$ = new Subject<void>();

  public showSetDefaultTipRef = false;

  public isNormalWidth = document.querySelector('body').offsetWidth >= 1920;

  public tooltipStr = '';

  public tipContext = {
    param: null as IWFViewWithMultiType | IWFView,
    isNormalWidth: this.isNormalWidth,
    isShowDesc: false,
    host: this.host,
    cmpWidth: this.cmpWidth,
    outputs: {
      close: (state: {
        value?: string;
        desc?: string;
        isClose: boolean;
        display?: string;
      }): void => {
        if (this.showSetDefaultTipRef) {
          if (!isNil(state?.value)) {
            if (this.host === 'json-input') {
              this.param.value.content = state.value;
            } else {
              this.param.value.default = state.value;
              this.param.value.display = state.display;
            }

            if (!Array.isArray(this.param.type) && !isNil(state?.desc)) {
              this.param.description = state.desc;
            }
          }

          if (state.isClose) {
            this.showSetDefaultTipRef = false;
            this.changeParam.emit();
          }
        }
      },
      valueChange: (state: {
        value?: string;
        desc?: string;
        isClose: boolean;
        display?: string;
      }): void => {
        if (!isNil(state?.value) && this.param.type.includes('file')) {
          if (this.host === 'json-input') {
            this.param.value.content = state.value;
          } else {
            this.param.value.default = state.value;
            this.param.value.display = state.display;
          }

          if (!Array.isArray(this.param.type) && !isNil(state?.desc)) {
            this.param.description = state.desc;
          }
          this.changeParam.emit();
        }
      },
    },
  };

  constructor(public nodeServ: NodeService) {}

  ngOnInit() {
    this.nodeServ
      .closeAllSetDefaultTipUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        if (this.showSetDefaultTipRef) {
          this.showSetDefaultTipRef = false;
        }
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.param?.currentValue) {
      const content = changes.param.currentValue.value.content;
      this.tooltipStr = typeof content === 'string'
        ? content
            .replace(/\r?\n/g, '')
            .replace(/\\/g, '')
            .replace(/^"(.*)"$/, '$1')
        : '';
      this.tipContext.param = changes.param.currentValue;
    }
  }

  public onClose = (state: {
    value?: string;
    desc?: string;
    isClose: boolean;
    display?: string;
  }): void => {
    if (!isNil(state?.value)) {
      if (this.host === 'json-input') {
        this.param.value.content = state.value;
      } else {
        this.param.value.default = state.value;
        this.param.value.display = state.display;
      }

      if (!Array.isArray(this.param.type) && !isNil(state?.desc)) {
        this.param.description = state.desc;
      }
    }

    if (state.isClose) {
      this.changeParam.emit();
    }
  };

  public onValueChange = (state: {
    value?: string;
    desc?: string;
    isClose: boolean;
    display?: string;
  }): void => {
    // array 形态 file 参数的 type 为 ['array<file>', 'image']，无精确 'file' 元素，
    // 需并列 array<file> 分支（与 set-default-tip saveFile/onClickOutside 守卫同口径），
    // 否则 array 默认值仅能在弹层关闭时经 close 路径写入，录入期不落库
    if (
      !isNil(state?.value) &&
      (this.param.type.includes('file') ||
        this.param.type.includes('array<file>'))
    ) {
      if (this.host === 'json-input') {
        this.param.value.content = state.value;
      } else {
        this.param.value.default = state.value;
        this.param.value.display = state.display;
      }

      if (!Array.isArray(this.param.type) && !isNil(state?.desc)) {
        this.param.description = state.desc;
      }
      this.changeParam.emit();
    }
  };

  public onSetDefault() {
    if (this.showSetDefaultTipRef) {
      this.showSetDefaultTipRef = false;
    } else {
      this.nodeServ.setCloseAllSetDefaultTip();
      this.showSetDefaultTipRef = true;
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
