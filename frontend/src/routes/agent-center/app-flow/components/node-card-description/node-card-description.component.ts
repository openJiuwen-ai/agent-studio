import { Component, OnInit, Input, SimpleChanges, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { MODULES } from '@shared/modules';
import { FlowUtils } from '@routes/agent-center/app-flow/utils/flow-utils';

@Component({
  selector: 'node-card-description',
  templateUrl: './node-card-description.component.html',
  styleUrls: ['./node-card-description.component.less'],
  standalone: true,
  imports: [MODULES],
  providers: [],
})
export class NodeCardDescriptionComponent implements OnInit {
  @Input() nodeInfo!: any;
  @Input() description?: string;
  @Input() originDescription?: string;

  public descriptionText = '';
  public showDescription = false;
  public isOverflow = false;

  @ViewChild('descEl') descEl: ElementRef;

  constructor(private cdr: ChangeDetectorRef) {}

  ngOnInit() {}

  private checkOverflow() {
    if (this.descEl?.nativeElement) {
      const el = this.descEl.nativeElement as HTMLElement;
      const overflow = el.scrollWidth > el.clientWidth;
      if (overflow !== this.isOverflow) {
        this.isOverflow = overflow;
        this.cdr.markForCheck();
      }
    }
  }

  initDescription() {
    const defaultDescription = FlowUtils.nodeDesci18nMap(this.nodeInfo?.type);
    this.showDescription = Boolean(this.description);
    this.descriptionText = this.description || this.originDescription || defaultDescription;
    setTimeout(() => this.checkOverflow());
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.initDescription();
  }
}
