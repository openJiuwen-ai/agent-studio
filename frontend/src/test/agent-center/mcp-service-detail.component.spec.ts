import { MCPServiceDetailComponent } from '../../routes/agent-center/app-mcp-service/mcp-service-detail/mcp-service-detail.component';

describe('MCPServiceDetailComponent tool refresh', () => {
  let component: any;

  beforeEach(() => {
    component = Object.create(MCPServiceDetailComponent.prototype);
    component.mcpServiceDetail = { tools: [] };
    component.selectedMcpTool = { name: 'old-tool' };
    component.selectedMcpToolParams = [{ key: 'old-param', value: { value: 'old-value' } }];
  });

  it('does not send old parameters when the refreshed tool has no schema', () => {
    const testMcpTools = jasmine.createSpy('testMcpTools').and.returnValue(Promise.resolve({}));
    component.api = { testMcpTools };
    component.serviceId = 'mcp-1';

    component.applyRefreshedTools({ tools: [{ name: 'new-tool' }] });
    component.testMcpTool();

    expect(component.selectedMcpToolParams).toEqual([]);
    expect(testMcpTools).toHaveBeenCalledWith({
      serviceId: 'mcp-1', toolName: 'new-tool', params: {},
    });
  });

  it('rebuilds parameters for the selected tool in a mixed list', () => {
    component.applyRefreshedTools({ tools: [
      { name: 'new-tool', inputSchema: { properties: { query: { type: 'string', value: 'new-value' } } } },
      { name: 'missing-schema' },
    ] });

    expect(component.selectedMcpToolParams.map((param: any) => param.key)).toEqual(['query']);
    expect(component.selectedMcpToolParams[0].value.value).toBe('new-value');
  });

  it('clears selection and parameters when the refreshed list is empty', () => {
    component.applyRefreshedTools({ tools: [] });

    expect(component.selectedMcpTool).toBeNull();
    expect(component.selectedMcpToolParams).toEqual([]);
  });
});
