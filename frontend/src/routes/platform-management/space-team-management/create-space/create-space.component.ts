import {
  Component,
  ElementRef,
  Input,
  OnDestroy,
  OnInit,
  ViewEncapsulation,
} from '@angular/core';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import {
  NzFormModule,
} from 'ng-zorro-antd/form';
import {
  NzInputModule,
} from 'ng-zorro-antd/input';
import {
  NzUploadModule,
  NzUploadFile,
} from 'ng-zorro-antd/upload';
import {
  NzButtonModule,
} from 'ng-zorro-antd/button';
import {
  NzIconModule,
} from 'ng-zorro-antd/icon';
import {
  AbstractControl,
  FormBuilder,
  FormControl,
  FormGroup,
  ValidationErrors,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { DEFAULT_ICON } from 'src/assets/images/common/common_image_base64';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import {NzMessageService} from "ng-zorro-antd/message";
import {getSessionStorage} from "../../../../utils/utils";
enum mapKeys {
  DEPLOY_URL = 'DEPLOY_URL',
  PUBLIC_URL = 'PUBLIC_URL'
}

@Component({
  selector: 'create-space',
  templateUrl: './create-space.component.html',
  styleUrls: ['./create-space.component.less'],
  styles: ['.create-space-modal { z-index:20 !important; }'],
  encapsulation: ViewEncapsulation.None,
  standalone: true,
  imports: [CommonModule, MODULES, ReactiveFormsModule, NzFormModule, NzInputModule, NzUploadModule, NzButtonModule, NzIconModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.PLATFORM_MANAGEMENT, I18nNamespace.COMMON],
    },
  ],
})
export class CreateSpaceComponent implements OnInit, OnDestroy {
  @Input() title;
  @Input() detail;
  @Input() source;
  public btnLoading = false;
  public myForm: FormGroup;
  baseUrl: string = window[mapKeys.DEPLOY_URL] + window[mapKeys.PUBLIC_URL] || '';
  logoIsError = false;
  upload_type = '.jpg,.jpeg,.png,.gif';
  max_size = 200 * 1024;
  logo = '';
  space_options = [];

  constructor(
    private fb: FormBuilder,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private i18n: I18NextEagerPipe,
    private modalRef: NzModalRef,
    private message: NzMessageService
  ) {
    this.space_options = getSessionStorage('SPACE_OPTIONS');
    this.myForm = this.fb.group({
      space_name: new FormControl('', [
        Validators.required,
        this.create_space_name_verify(),
        Validators.maxLength(64)
      ]),
      space_description: new FormControl('', Validators.maxLength(256)),
      logo: new FormControl('', [Validators.required]),
    });
  }

  ngOnInit() {
    if (this.source === 'edit') {
      this.myForm.controls.space_name.setValue(this.detail.name);
      this.myForm.controls.space_description.setValue(this.detail.description);
      this.myForm.controls.logo.setValue(this.detail.icon);
    } else {
      this.myForm.controls.logo.setValue(DEFAULT_ICON);
    }
  }

  ngOnDestroy(): void {}

  isConfirmBtnDisabled() {
    return this.myForm.get('space_name').invalid || this.myForm.getRawValue().space_name.length > 64 || this.myForm.getRawValue().space_description.length > 256;
  }

  getIcon(url: string) {
    if (url.startsWith('data:image/')) {
      return url;
    } else {
      return cdnAssetUrl(url);
    }
  }

  create_space_name_verify() {
    return (control: AbstractControl): ValidationErrors | null => {
      const _val = control.value as string;
      const is_has =
        this.source === 'edit'
          ? this.space_options?.filter(
              (item) => this.detail.id !== item.id && item.name === _val,
            )
          : this.space_options?.filter((item) => item.name === _val);
      if (is_has?.length > 0) {
        return {
          serviceName: {
            message: this.i18n.transform('duplicate_name'),
          },
        };
      }
      if (
        /^[\u4e00-\u9fa5a-zA-Z0-9_（）()！!-](?:[\u4e00-\u9fa5a-zA-Z0-9_（）()！! -]*[\u4e00-\u9fa5a-zA-Z0-9_（）()！!-])?$/.test(
          _val,
        )
      ) {
        return null;
      }
      return {
        serviceName: {
          message:
            this.i18n.transform('chars_validator'),
        },
      };
    };
  }

  dismiss() {
    this.modalRef.close();
  }

  close() {
    this.modalRef.destroy();
  }

  submit() {
    if (this.source === 'edit') {
      this.editSpace();
    } else {
      this.createSpace();
    }
  }

  editSpace() {
    if (!this.checkGroup()) {
      return;
    }
    const sapce_info = this.handleAutoInfo();
    sapce_info.id = this.detail.id;
    this.spaceTeamManagementService.putWorkspace(sapce_info).then((res) => {
      this.close();
      this.message.create('success', this.i18n.transform('modify_space_success'));
    });
  }

  createSpace() {
    if (!this.checkGroup()) {
      return;
    }
    const sapce_info = this.handleAutoInfo();

    this.spaceTeamManagementService
      .postWorkspace(sapce_info)
      .then((res) => {
        this.close();
        this.message.create('success', this.i18n.transform('create_space_success'));
        this.spaceTeamManagementService.updateSpace('Create');
      })
      .catch((err) => {
        const error_code = getSessionStorage('error_code');
        if (['Openjiuwen.02001064', 'Openjiuwen.02001022'].includes(error_code)) {
          this.close();
        }
      });
  }

  checkGroup(): boolean {
    const errors: ValidationErrors | null = null;
    this.logoIsError = null;
    return true;
  }

  beforeUpload = (file: NzUploadFile): boolean => {
    const isImage = file.type?.startsWith('image/');
    const isLt200k = file.size !== undefined && file.size < this.max_size;
    if (!isImage) {
      this.message.create('error', this.i18n.transform('support_upload_image_format',{types:this.upload_type}));
      return false;
    }
    if (!isLt200k) {
      this.message.create('error', this.i18n.transform('image_size_limit',{max_size:this.max_size/1024}));
      return false;
    }
    this.logoIsError = false;
    const reader = new FileReader();
    reader.readAsDataURL(file as any);
    reader.onload = () => {
      this.myForm.controls.logo.setValue(reader.result);
    };
    return false;
  };

  //创建更新处理鉴权信息
  handleAutoInfo() {
    const value = this.myForm.getRawValue();
    const params: any = {
      name: value.space_name,
      description: value.space_description,
      icon: value.logo,
    };
    return params;
  }

  editLogo() {
    this.myForm.controls.logo.setValue('');
  }
}
