import { rewriteTemplateInputRefs } from '../routes/agent-center/app-flow/components/template-transform-modal/rewrite-template-input-refs';

describe('rewriteTemplateInputRefs', () => {
  it('重命名 data 时不误伤 data_items', () => {
    const tpl = '{{ data }} and {{ data_items }}';
    expect(rewriteTemplateInputRefs(tpl, 'data', 'foo')).toBe('{{ foo }} and {{ data_items }}');
  });

  it('支持无空格与属性/过滤器/下标边界', () => {
    expect(rewriteTemplateInputRefs('{{data}}', 'data', 'foo')).toBe('{{foo}}');
    expect(rewriteTemplateInputRefs("{{ data.get('x') }}", 'data', 'foo')).toBe("{{ foo.get('x') }}");
    expect(rewriteTemplateInputRefs('{{ data|length }}', 'data', 'foo')).toBe('{{ foo|length }}');
    expect(rewriteTemplateInputRefs("{{ data['k'] }}", 'data', 'foo')).toBe("{{ foo['k'] }}");
  });

  it('newName 含 $ 时不被当成替换回溯引用', () => {
    expect(rewriteTemplateInputRefs('{{ data }}', 'data', 'a$1b')).toBe('{{ a$1b }}');
  });
});
