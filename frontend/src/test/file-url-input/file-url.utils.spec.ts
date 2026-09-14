import {
  checkFileUrl,
  createUrlFileItem,
  getDataUriExtension,
  getUrlDisplayName,
  getUrlExtension,
  isExtensionAllowed,
  isSupportedUrlType,
  splitUrlText,
} from '../../routes/agent-center/file-url.utils';

// 特性「开始节点支持URL方式」：URL 校验纯函数。
// 规则：协议头 ∈ {http:, https:, data:}；扩展名白名单复用上传口径
// （image: png/jpg/jpeg/gif/webp/svg；video: mp4/avi/rmvb/mkv/flv/f4v/wmv/3gp）；
// 仅 image/video 子类型（含 array 形态）开放 URL 模式。

describe('file-url.utils — URL 录入校验', () => {
  describe('isSupportedUrlType', () => {
    it('image/video 子类型（含 array 形态）支持 URL 模式', () => {
      expect(isSupportedUrlType('file/image')).toBe(true);
      expect(isSupportedUrlType('file/video')).toBe(true);
      expect(isSupportedUrlType('array<file/image>')).toBe(true);
      expect(isSupportedUrlType('array<file/video>')).toBe(true);
    });

    it('其余 file 子类型不支持', () => {
      expect(isSupportedUrlType('file/doc')).toBe(false);
      expect(isSupportedUrlType('file/txt')).toBe(false);
      expect(isSupportedUrlType('file/audio')).toBe(false);
      expect(isSupportedUrlType('file/default')).toBe(false);
      expect(isSupportedUrlType('array<file/default>')).toBe(false);
      expect(isSupportedUrlType('string')).toBe(false);
      expect(isSupportedUrlType('')).toBe(false);
    });
  });

  describe('checkFileUrl', () => {
    it('合法 http/https URL（含预签名 query）通过', () => {
      expect(
        checkFileUrl(
          'https://minio.example.com/bucket/photo.png?X-Amz-Signature=abc123',
          'file/image',
        ),
      ).toBeNull();
      expect(
        checkFileUrl('http://example.com/a.jpg', 'file/image'),
      ).toBeNull();
    });

    it('扩展名大写不区分大小写', () => {
      expect(checkFileUrl('https://example.com/a.PNG', 'file/image')).toBeNull();
    });

    it('路径含 URL 编码字符（如中文对象名）通过', () => {
      expect(
        checkFileUrl('https://example.com/%E6%8A%93%E6%8B%8D.png', 'file/image'),
      ).toBeNull();
    });

    it('非法协议头被拦截', () => {
      expect(checkFileUrl('ftp://example.com/a.png', 'file/image')).toBe(
        'url_invalid_protocol',
      );
      expect(checkFileUrl('javascript:alert(1)', 'file/image')).toBe(
        'url_invalid_protocol',
      );
      expect(checkFileUrl('file:///etc/passwd.png', 'file/image')).toBe(
        'url_invalid_protocol',
      );
    });

    it('格式非法被拦截', () => {
      expect(checkFileUrl('not-a-url', 'file/image')).toBe(
        'url_invalid_format',
      );
      expect(checkFileUrl('   ', 'file/image')).toBe('url_invalid_format');
      expect(checkFileUrl('', 'file/image')).toBe('url_invalid_format');
      expect(checkFileUrl('/relative/path.png', 'file/image')).toBe(
        'url_invalid_format',
      );
    });

    it('扩展名不在白名单被拦截', () => {
      expect(checkFileUrl('https://example.com/a.txt', 'file/image')).toBe(
        'url_invalid_extension',
      );
      expect(checkFileUrl('https://example.com/a.exe', 'file/image')).toBe(
        'url_invalid_extension',
      );
      expect(checkFileUrl('https://example.com/a.png', 'file/video')).toBe(
        'url_invalid_extension',
      );
    });

    it('无扩展名被拦截（预签名 query 不影响判断）', () => {
      expect(
        checkFileUrl('https://example.com/get-object?file=a.png', 'file/image'),
      ).toBe('url_invalid_extension');
      expect(checkFileUrl('https://example.com/path/', 'file/image')).toBe(
        'url_invalid_extension',
      );
    });

    it('video 类型白名单校验', () => {
      expect(checkFileUrl('https://example.com/a.mp4', 'file/video')).toBeNull();
      expect(checkFileUrl('https://example.com/a.flv', 'file/video')).toBeNull();
      expect(
        checkFileUrl('https://example.com/a.mov', 'array<file/video>'),
      ).toBe('url_invalid_extension');
    });

    it('data: URI 按 mediatype 映射白名单', () => {
      expect(
        checkFileUrl('data:image/png;base64,iVBORw0KGgo=', 'file/image'),
      ).toBeNull();
      expect(
        checkFileUrl('data:image/svg+xml;base64,PHN2Zy8+', 'file/image'),
      ).toBeNull();
      expect(
        checkFileUrl('data:video/mp4;base64,AAAA', 'file/video'),
      ).toBeNull();
      // 白名单外 mediatype / 缺失 mediatype 均拦截
      expect(
        checkFileUrl('data:image/bmp;base64,AAAA', 'file/image'),
      ).toBe('url_invalid_extension');
      expect(checkFileUrl('data:,hello', 'file/image')).toBe(
        'url_invalid_extension',
      );
      expect(
        checkFileUrl('data:image/png;base64,AAAA', 'file/video'),
      ).toBe('url_invalid_extension');
    });
  });

  describe('getUrlExtension / getDataUriExtension', () => {
    it('取 path 末段扩展名（自动剥离 query）', () => {
      const parsed = new URL(
        'https://example.com/bucket/a/b/photo.jpeg?sig=1&x=2',
      );
      expect(getUrlExtension(parsed)).toBe('jpeg');
    });

    it('data: URI mediatype 映射', () => {
      expect(getDataUriExtension('data:image/png;base64,x')).toBe('png');
      expect(getDataUriExtension('data:IMAGE/JPEG;base64,x')).toBe('jpg');
      expect(getDataUriExtension('data:application/pdf,x')).toBeNull();
    });
  });

  describe('getUrlDisplayName', () => {
    it('path 末段为显示名', () => {
      expect(
        getUrlDisplayName('https://example.com/bucket/pic.png?sig=1'),
      ).toBe('pic.png');
    });

    it('URL 编码对象名被解码', () => {
      expect(
        getUrlDisplayName('https://example.com/%E6%8A%93%E6%8B%8D.png'),
      ).toBe('抓拍.png');
    });

    it('data: URI 以 mediatype 合成显示名', () => {
      expect(getUrlDisplayName('data:image/png;base64,x')).toBe('data.png');
    });

    it('非法输入回退 unknown', () => {
      expect(getUrlDisplayName('')).toBe('unknown');
      expect(getUrlDisplayName('https://example.com/')).toBe('unknown');
    });
  });

  describe('splitUrlText', () => {
    it('按换行拆分并剔除空行（兼容 CRLF）', () => {
      expect(
        splitUrlText('https://a.com/1.png\r\n\r\n  https://a.com/2.png \n\n'),
      ).toEqual(['https://a.com/1.png', 'https://a.com/2.png']);
      expect(splitUrlText('')).toEqual([]);
      expect(splitUrlText('   \n  ')).toEqual([]);
    });
  });

  describe('createUrlFileItem', () => {
    it('产出与上传产物同构的条目（succeeded + fromUrl 标记）', () => {
      const item = createUrlFileItem('https://example.com/pic.png');
      expect(item.url).toBe('https://example.com/pic.png');
      expect(item.name).toBe('pic.png');
      expect(item.progress).toBe('succeeded');
      expect(item.fromUrl).toBe(true);
      expect(item.fileId).toBeTruthy();
      expect(item.controller).toBeTruthy();
    });
  });

  describe('isExtensionAllowed', () => {
    it('与上传白名单同源', () => {
      expect(isExtensionAllowed('png', 'file/image')).toBe(true);
      expect(isExtensionAllowed('.svg', 'array<file/image>')).toBe(true);
      expect(isExtensionAllowed('mp4', 'file/video')).toBe(true);
      expect(isExtensionAllowed('png', 'file/video')).toBe(false);
    });
  });
});
