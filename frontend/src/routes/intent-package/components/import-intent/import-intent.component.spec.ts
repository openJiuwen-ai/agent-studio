import { ElementRef } from '@angular/core';
import { ImportIntentModalComponent } from './import-intent.component';

describe('ImportIntentModalComponent', () => {
  it('clears the selected file and native file input', () => {
    const component = new ImportIntentModalComponent(
      {} as any,
      {} as any,
      {} as any,
      {} as any,
      {},
    );
    const nativeElement = { value: 'intents.xlsx' } as HTMLInputElement;
    component.fileInput = new ElementRef(nativeElement);
    component.uplaodFile = {
      name: 'intents.xlsx',
      file: {} as File,
    };

    component.removeFile();

    expect(component.uplaodFile).toEqual({});
    expect(nativeElement.value).toBe('');
  });

  it('does not submit the same import more than once while a request is pending', () => {
    const uploadIntent = jasmine.createSpy('uploadIntent').and.returnValue(new Promise(() => {}));
    const component = new ImportIntentModalComponent(
      {} as any,
      { uploadIntent } as any,
      {} as any,
      {} as any,
      { intentId: 'intent-1', intentName: 'intent-name' },
    );
    component.uplaodFile = { file: {} as File };

    component.importIntent();
    component.importIntent();

    expect(uploadIntent).toHaveBeenCalledTimes(1);
    expect(component.isLoading).toBe(true);
  });
});
