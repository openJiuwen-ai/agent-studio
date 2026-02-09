from typing import Any

from openjiuwen.core.workflow import WorkflowComponent, Input, Output
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.session.node import Session


class EmptyComponent(WorkflowComponent):
    def __init__(self) -> None:
        super().__init__()

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        return inputs
