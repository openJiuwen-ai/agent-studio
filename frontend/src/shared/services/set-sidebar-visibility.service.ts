import { ChangeDetectorRef, Injectable } from '@angular/core';
import { WindowResizeService } from '@shared/base/window-resize.service';

@Injectable({
  providedIn: 'root',
})
export class SetSidebarVisibilityService {
  private consoleContainerPaddingLeft = '';

  constructor(private windowResizeService: WindowResizeService) {}

  /** 隐藏左边菜单栏 */
  public setSidebarsVisibilityByState(
    state: string,
    isNeedHideContainer: boolean = false, // 屏蔽内容区高度
  ): void {
    const HWCloudTopHeight: number =
      this.windowResizeService.getHWCloudTopHeight();
    const consoleSidebar = document.querySelector('#J_sidebar');
    const consoleHeader = document.querySelector('#J_header');

    //左侧菜单栏修改为自定义
    const menuSidebar = document.querySelector('left-menu');
    const content = document.querySelector('tp-layout-content');
    const header = document.querySelector('ti-app-layout-header'); //layout 头部，公共弹窗相对布局
    const layoutHeaderHeight = header?.clientHeight || 0;
    const consoleContainer = document.querySelector(
      '#J_container',
    ) as HTMLDivElement;

    if (state === 'hideHeader') {
      consoleHeader?.setAttribute('style', 'display:none;');
      consoleContainer.style.paddingTop = '0px';
    }

    if (state === 'hideSidebar') {
      consoleSidebar?.setAttribute('style', 'display: none');
      content?.setAttribute(
        'style',
        `padding-left: 0px !important;height:calc(100vh - ${HWCloudTopHeight + layoutHeaderHeight}px)`,
      );
      setTimeout(() => {
        consoleContainer.style.paddingLeft = '0px';
      }, 1000);
    }

    if (state === 'init') {
      consoleSidebar?.setAttribute('style', 'display: none');
      menuSidebar?.setAttribute('style', 'display: none');
      content?.setAttribute(
        'style',
        `margin-left: 0px !important;  width: 100% !important; height:calc(100vh - ${HWCloudTopHeight + layoutHeaderHeight}px)`,
      );
      // 存储原始 JContainer 的 paddingLeft 值
      this.consoleContainerPaddingLeft = consoleContainer.style.paddingLeft;
      consoleContainer.style.paddingLeft = '0px';
    }

    if (state === 'destroy') {
      consoleSidebar?.setAttribute('style', 'display: none');
      menuSidebar?.setAttribute('style', '');
      content?.setAttribute('style', `height:calc(100vh - ${HWCloudTopHeight + layoutHeaderHeight}px)`);
      consoleContainer.style.paddingLeft = this.consoleContainerPaddingLeft;
      content?.removeAttribute('data-set');
    }
    if (state === null || isNeedHideContainer) {
      content?.setAttribute('data-set', 'layout-page');
    }
    // 专家·技能mcp使用vh计算，导致出现双滚动条，待优化
    if(layoutHeaderHeight > 0){
      content?.classList.add('layoutContentHasHeader');
    }else{
      content?.classList.remove('layoutContentHasHeader');
    }
  }
}
