import { NzUploadFile } from 'ng-zorro-antd/upload';
import { ImportTemplateModalComponent } from './import-template-modal.component';

describe('ImportTemplateModalComponent', () => {
  let component: ImportTemplateModalComponent;
  let message: { error: jasmine.Spy };
  let i18n: { transform: jasmine.Spy };

  beforeEach(() => {
    message = { error: jasmine.createSpy('error') };
    i18n = {
      transform: jasmine.createSpy('transform').and.callFake((key: string) => key),
    };
    component = new ImportTemplateModalComponent(
      {} as any,
      i18n as any,
      message as any,
      {} as any,
      { markForCheck: jasmine.createSpy('markForCheck') } as any,
    );
  });

  function createUploadFile(name: string, size: number): NzUploadFile {
    return {
      uid: name,
      name,
      size,
      type: 'application/octet-stream',
      _file: { name, size },
    } as unknown as NzUploadFile;
  }

  it('rejects files other than xls and xlsx', () => {
    const file = createUploadFile('templates.csv', 1024);

    expect(component.beforeUpload(file)).toBe(false);
    expect(message.error).toHaveBeenCalledWith('file_wrong_type');
    expect(i18n.transform).toHaveBeenCalledWith('file_wrong_type', { name: 'templates.csv' });
    expect(component.fileList).toEqual([]);
    expect(component.selectedFile).toBeNull();
  });

  it('rejects files larger than 20MB', () => {
    const file = createUploadFile('templates.xlsx', component.maxSize + 1);

    expect(component.beforeUpload(file)).toBe(false);
    expect(message.error).toHaveBeenCalledWith('file_size_cannot_exceed');
    expect(i18n.transform).toHaveBeenCalledWith('file_size_cannot_exceed', { size: 20 });
    expect(component.fileList).toEqual([]);
    expect(component.selectedFile).toBeNull();
  });

  it('accepts xls and xlsx files up to and including 20MB', () => {
    const file = createUploadFile('TEMPLATES.XLSX', component.maxSize);

    expect(component.beforeUpload(file)).toBe(false);
    expect(message.error).not.toHaveBeenCalled();
    expect(component.fileList).toEqual([file]);
    expect(component.selectedFile).toBe(file);
  });
});
