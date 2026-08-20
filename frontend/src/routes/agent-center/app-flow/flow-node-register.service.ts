import { Injectable, Injector } from '@angular/core';
import { Dom, Graph, Path } from '@antv/x6';
import { register, AngularShapeView } from '@antv/x6-angular-shape';

const proto = AngularShapeView.prototype as any;
const origUnmount = proto.unmountAngularContent;
proto.unmountAngularContent = function () {
  if (!this.getNodeContainer()) {
    return null;
  }
  return origUnmount.call(this);
};
import { AgentNodeComponent } from './components/agent-node/agent-node.component';
import { AggregationNodeComponent } from './components/aggregation-node/aggregation-node.component';
import { BranchNodeComponent } from './components/branch-node/branch-node.component';
import { ChildFlowComponent } from './components/child-flow-node/child-flow.component';
import { CodeNodeComponent } from './components/code-node/code-node.component';
import { CommentNodeComponent } from './components/comment-node/comment-node.component';
import { ControllerNodeComponent } from './components/controller-node/controller-node.component';
import { EmptyNodeComponent } from './components/empty-node/empty-node.component';
import { EndNodeComponent } from './components/end-node/end-node.component';
import { ExceptionNodeComponent } from './components/exception-node/exception-node.component';
import { InputNodeComponent } from './components/input-node/input-node.component';
import { IntentContainerNodeComponent } from './components/intent-container-node/intent-container-node.component';
import { IntentNodeComponent } from './components/intent-node/intent-node.component';
import { KnowledgeNodeComponent } from './components/knowledge-node/knowledge-node.component';
import { LlmNodeComponent } from './components/llm-node/llm-node.component';
import { LoopInputNodeComponent } from './components/loop-input-node/loop-input-node.component';
import { LoopNodeComponent } from './components/loop-node/loop-node.component';
import { LoopOutputNodeComponent } from './components/loop-output-node/loop-output-node.component';
import { MCPServicenNodeComponent } from './components/mcp-service-node/mcp-service-node.component';
import { MessageNodeComponent } from './components/message-node/message-node.component';
import { ParamExtractionNodeComponent } from './components/param-extraction-node/param-extraction-node.component';
import { PluginNodeComponent } from './components/plugin-node/plugin-node.component';
import { QANodeComponent } from './components/QA-node/QA-node.component';
import { QuestionerNodeComponent } from './components/questioner-node/questioner-node.component';
import { SetVariableNodeComponent } from './components/set-variable-node/set-variable-node.component';
import { SingleAgentNodeComponent } from './components/single-agent-node/single-agent-node.component';
import { SqlNodeComponent } from './components/sql-node/sql-node.component';
import { StartNodeComponent } from './components/start-node/start-node.component';
import { SubControllerNodeComponent } from './components/sub-controller-node/sub-controller-node.component';
import { SubWorkflowNodeComponent } from './components/sub-workflow-node/sub-workflow-node.component';
import { WorkflowNodeComponent } from './components/workflow-node/workflow-node.component';
import { FLOW_COLORS, NODE_NAMES, NODE_SIZE } from './flow.const';
import { TargetMarker } from './utils/flow-utils';
import { StreamTransformNodeComponent } from './components/stream-transform-node/stream-transform-node.component';

interface IControlParams {
  pos: 'top' | 'right' | 'bottom' | 'left';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  c: number;
}

@Injectable({
  providedIn: 'root',
})
export class FlowNodeRegisterService {
  public registerComponents(injector: Injector) {
    this.registerConnector();
    this.registerGrid();
    this.registerDagEdge();
    this.registerLLMNode(injector);
    this.registerPluginNode(injector);
    this.registerStartEndNode(injector);
    this.registerEmptyNode(injector);
    this.registerBranchNode(injector);
    this.registerCodeNode(injector);
    this.registerChildFlow(injector);
    this.registerQuestionerNode(injector);
    this.registerIntentNode(injector);
    this.registerComplexIntentDetection(injector);
    this.registerMessageNode(injector);
    this.registerKnowledgeNode(injector);
    this.registerAggregationNode(injector);
    this.registerInputNode(injector);
    this.registerLoopNode(injector);
    this.registerSetVariableNode(injector);
    this.registerLoopInputNode(injector);
    this.registerLoopOutputNode(injector);
    this.registerMcpNode(injector);
    this.registerDataProcessNode(injector);
    this.registerDataSynthesisNode(injector);
    this.registerIntentContainerNode(injector);
    this.registerAgentNode(injector);
    this.registerControllerNode(injector);
    this.registerSubControllerNode(injector);
    this.registerWorkflowNode(injector);
    this.registerSingleAgentNode(injector);
    this.registerSubWorkflowNode(injector);
    this.registerQANode(injector);
    this.registerSqlNode(injector);
    this.registerExceptionNode(injector);
    this.registerParamExtractionNode(injector);
    this.registerCommentNode(injector);
    this.registerStreamTransformNode(injector);
  }

  public unregisterComponents() {
    Graph.unregisterGrid('plus-pattern');
    Graph.unregisterConnector('bezier');
    Graph.unregisterEdge('dag-edge');
    NODE_NAMES.forEach((name) => {
      Graph.unregisterNode(`op-${name}-node`);
    });
  }

  private registerGrid() {
    Graph.registerGrid('plus-pattern', {
      markup: 'path',
      color: '#e7ebed',
      thickness: 0.8,
      update(elem, options) {
        // 加号的大小 size * size
        const size = 6;
        const thickness = options.thickness * options.sx;

        const pathData = `
          M ${size / 2} 0
          V ${size}
          M 0 ${size / 2}
          H ${size}
        `;

        Dom.attr(elem, {
          d: pathData,
          stroke: options.color,
          'stroke-width': thickness,
          fill: 'none',
          'stroke-linecap': 'butt',
        });
      },
    });
  }


  private registerConnector(): void {
    Graph.registerConnector(
      'bezier',
      (sourcePoint, targetPoint) => {
        const path = new Path();
        const curvature = 0.45;

        const getControlWithCurvature = ({
          pos,
          x1,
          y1,
          x2,
          y2,
          c,
        }: IControlParams) => {
          const dx = Math.abs(x2 - x1) * c;
          const dy = Math.abs(y2 - y1) * c;

          let controlX = 0;
          let controlY = 0;

          if (pos === 'top') {
            controlX = x1;
            controlY = y1 - dy;
          } else if (pos === 'bottom') {
            controlX = x1;
            controlY = y1 + dy;
          } else if (pos === 'left') {
            controlX = x1 - dx;
            controlY = y1;
          } else {
            // right
            controlX = x1 + dx;
            controlY = y1;
          }

          return [controlX, controlY];
        };

        // 根据源点和目标点的位置确定控制点
        const [sourceControlX, sourceControlY] = getControlWithCurvature({
          pos: 'right',
          x1: sourcePoint.x,
          y1: sourcePoint.y,
          x2: targetPoint.x,
          y2: targetPoint.y,
          c: curvature,
        });

        const [targetControlX, targetControlY] = getControlWithCurvature({
          pos: 'left',
          x1: targetPoint.x,
          y1: targetPoint.y,
          x2: sourcePoint.x,
          y2: sourcePoint.y,
          c: curvature,
        });

        path.appendSegment(
          Path.createSegment('M', sourcePoint.x, sourcePoint.y),
        );

        path.appendSegment(
          Path.createSegment(
            'C',
            sourceControlX,
            sourceControlY,
            targetControlX,
            targetControlY,
            targetPoint.x,
            targetPoint.y,
          ),
        );

        return path.serialize();
      },
      true,
    );
  }

  private registerDagEdge() {
    Graph.registerEdge(
      'dag-edge',
      {
        inherit: 'edge',
        attrs: {
          line: {
            stroke: FLOW_COLORS.connected,
            strokeWidth: 2,
            targetMarker: TargetMarker,
          },
        },
      },
      true,
    );
  }

  private registerLLMNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-llm-node', injector, LlmNodeComponent),
    );
  }

  private registerQuestionerNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-questioner-node',
        injector,
        QuestionerNodeComponent,
      ),
    );
  }

  private registerPluginNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-plugin-node', injector, PluginNodeComponent),
    );
  }

  private registerCodeNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-code-node', injector, CodeNodeComponent),
    );
  }

  private registerChildFlow(injector: Injector) {
    register(
      this.commonRegisterNode('op-workflow-node', injector, ChildFlowComponent),
    );
  }

  private registerStartEndNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-start-node', injector, StartNodeComponent),
    );

    register(
      this.commonRegisterNode('op-end-node', injector, EndNodeComponent),
    );
  }

  private registerEmptyNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-empty-node', injector, EmptyNodeComponent),
    );
  }

  private registerBranchNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-branch-node', injector, BranchNodeComponent),
    );
  }

  private registerIntentNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-intentdetection-node',
        injector,
        IntentNodeComponent,
      ),
    );
  }

  private registerComplexIntentDetection(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-complexintentdetection-node',
        injector,
        IntentNodeComponent,
      ),
    );
  }

  private registerMessageNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-message-node',
        injector,
        MessageNodeComponent,
      ),
    );
  }

  private registerStreamTransformNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-streamtransform-node',
        injector,
        StreamTransformNodeComponent,
      ),
    );
  }

  private registerKnowledgeNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-knowledgerepo-node',
        injector,
        KnowledgeNodeComponent,
      ),
    );
  }

  private registerAggregationNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-aggregation-node',
        injector,
        AggregationNodeComponent,
      ),
    );
  }

  private registerInputNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-input-node', injector, InputNodeComponent),
    );
  }

  private registerLoopNode(injector: Injector) {
    register({
      shape: 'op-loop-node',
      width: NODE_SIZE.width * 2,
      height: NODE_SIZE.height * 6,
      content: LoopNodeComponent,
      injector,
    });
  }

  private registerSetVariableNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-setvariable-node',
        injector,
        SetVariableNodeComponent,
      ),
    );
  }

  private registerLoopInputNode(injector: Injector) {
    register({
      shape: 'op-loopinput-node',
      width: NODE_SIZE.width / 2,
      height: NODE_SIZE.loopIO,
      content: LoopInputNodeComponent,
      injector,
    });
  }

  private registerLoopOutputNode(injector: Injector) {
    register({
      shape: 'op-loopoutput-node',
      width: NODE_SIZE.width / 2,
      height: NODE_SIZE.loopIO,
      content: LoopOutputNodeComponent,
      injector,
    });
  }

  private registerMcpNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-mcp-node',
        injector,
        MCPServicenNodeComponent,
      ),
    );
  }

  private registerDataProcessNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-dataprocess-node',
        injector,
        MCPServicenNodeComponent,
      ),
    );
  }

  private registerDataSynthesisNode(injector: Injector) {
    register({
      shape: 'op-datasynthesis-node',
      width: NODE_SIZE.width,
      height: NODE_SIZE.height,
      content: MCPServicenNodeComponent,
      injector,
    });
  }

  private registerAgentNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-agent-node', injector, AgentNodeComponent),
    );
  }

  private registerIntentContainerNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-intentdetectioncontainer-node',
        injector,
        IntentContainerNodeComponent,
      ),
    );
  }

  private registerControllerNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-controller-node',
        injector,
        ControllerNodeComponent,
      ),
    );
  }

  private registerSubControllerNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-subcontroller-node',
        injector,
        SubControllerNodeComponent,
      ),
    );
  }

  private registerWorkflowNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-workflow-multi-node',
        injector,
        WorkflowNodeComponent,
      ),
    );
  }

  private registerSingleAgentNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-single-agent-node',
        injector,
        SingleAgentNodeComponent,
      ),
    );
  }

  private registerSubWorkflowNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-subWorkflow-multi-node',
        injector,
        SubWorkflowNodeComponent,
      ),
    );
  }

  private registerQANode(injector: Injector) {
    register(this.commonRegisterNode('op-qa-node', injector, QANodeComponent));
  }

  private registerSqlNode(injector: Injector) {
    register(
      this.commonRegisterNode('op-sql-node', injector, SqlNodeComponent),
    );
  }

  private registerExceptionNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-structuredmessagesexception-node',
        injector,
        ExceptionNodeComponent,
      ),
    );
  }

  private registerParamExtractionNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-paramextraction-node',
        injector,
        ParamExtractionNodeComponent,
      ),
    );
  }

  private registerCommentNode(injector: Injector) {
    register(
      this.commonRegisterNode(
        'op-comment-node',
        injector,
        CommentNodeComponent,
      ),
    );
  }

  private commonRegisterNode(shape: string, injector: Injector, content: any) {
    return {
      shape: shape,
      width: NODE_SIZE.width,
      height: NODE_SIZE.height,
      content: content,
      injector,
    };
  }
}
