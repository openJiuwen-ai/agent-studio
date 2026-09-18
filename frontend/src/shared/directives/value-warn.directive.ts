import {
  AfterViewInit,
  Directive,
  ElementRef,
  Input,
  OnInit,
  OnChanges,
  SimpleChanges,
} from '@angular/core';

@Directive({
  selector: '[valueWarn]',
  standalone: true,
})
export class ValueWarnDirective implements OnInit, OnChanges {

  @Input('valueWarn') data: any;

  constructor(private el: ElementRef) { }

  ngOnInit() {
    this.updateColor();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes?.data) {
      this.updateColor();
    }
  }
  /**
  * textContent 内容
  * isParamName 参数名字 做正则校验
  * noRequired 参数值不必填的 ，必填校验空,默认必填，非必填才传此参数
  * refWithout 引用的值 不存在了
  * isInteger 整数
  * hasInvalidDescendant 后代字段名违规（父字段自身名合法时，用于向上传递高亮）
  *
  */
  private updateColor() {
    const element = this.el.nativeElement;
    element.classList.remove('!text-[#FF8800]')
    let showWarn;
    // 校验值数据是否在  必填 && 为空
    if (!this.data.textContent) {
      if (this.data.textContent === 0 || this.data.textContent === false) {
        showWarn = false;
      } else {
        showWarn = !this.data.noRequired;
      }
    } else {
      // 是名字，不符合规范
      if (this.data.isParamName && !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(this.data.textContent as string)) {
        showWarn = true;
      }

      // 是整数，不符合规范
      if (this.data.isInteger && !this.isIntegerStr(this.data.textContent)) {
        showWarn = true;
      }

      // 引用的值 不存在了
      if (this.data.refWithout) {
        showWarn = true;
      }
    }

    // 后代字段名违规，向上传递高亮（父字段自身名可能合法）
    if (this.data.hasInvalidDescendant) {
      showWarn = true;
    }


    if (showWarn) {
      element.classList.add('!text-[#FF8800]');
    }
  }

  isIntegerStr(value: string | number): boolean {
    if (typeof value === 'number') {
      return true;
    }

    const num = Number(value);
    return !Number.isNaN(num) && Number.isInteger(num);
  };
}
