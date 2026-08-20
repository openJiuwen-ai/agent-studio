import { ElementRef } from '@angular/core';
import { ImportPackageModalComponent } from './import-package-modal.component';

describe('ImportPackageModalComponent', () => {
  it('clears the selected file and native file input', () => {
    const component = new ImportPackageModalComponent(
      {} as any,
      {} as any,
      {} as any,
      {} as any,
      {} as any,
      {},
    );
    const nativeElement = { value: 'intent-package.xlsx' } as HTMLInputElement;
    component.fileInput = new ElementRef(nativeElement);
    component.uplaodFile = {
      name: 'intent-package.xlsx',
      file: {} as File,
    };

    component.removeFile();

    expect(component.uplaodFile).toEqual({});
    expect(nativeElement.value).toBe('');
  });

  it('does not submit the same import more than once while a request is pending', () => {
    const uploadFile = jasmine.createSpy('uploadFile').and.returnValue(new Promise(() => {}));
    const component = new ImportPackageModalComponent(
      { uploadFile } as any,
      {} as any,
      {} as any,
      {} as any,
      {} as any,
      {},
    );
    component.uplaodFile = { file: {} as File };

    component.importIntent();
    component.importIntent();

    expect(uploadFile).toHaveBeenCalledTimes(1);
    expect(component.isLoading).toBe(true);
  });
});
