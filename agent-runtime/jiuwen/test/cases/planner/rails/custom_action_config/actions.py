"""mock jiuwen-supported action for debug"""

from typing import Optional, Dict, Any

from jiuwen.planner.rails.common.decorator import action
from jiuwen.planner.rails.config import ActionConfig


@action
def mock_action(
    context: Optional[dict] = None,
    config: Optional[ActionConfig] = None,
) -> Dict[str, Any]:
    print("execute mock action")
    return dict(query="更新后的query")


@action
def mock_action_append(
    context: Optional[dict] = None,
    config: Optional[ActionConfig] = None,
) -> Dict[str, Any]:
    print("execute mock action")
    query = context.get("query")
    return dict(query=query + "追加更新")


@action
def mock_execution_action(
    context: Optional[dict] = None,
    config: Optional[ActionConfig] = None,
) -> Dict[str, Any]:
    return dict(arguments="更新后的arguments")
