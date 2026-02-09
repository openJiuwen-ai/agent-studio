import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Tuple

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common.dsl import ErrorBody


class Args:
    def __init__(self, params: Dict[str, Any]) -> None:
        self.params: Dict[str, Any] = params


class Outputs(dict):
    pass


class CodeRunner(ABC):

    @abstractmethod
    async def run(self, code_language: str, code_str: str, timeout: float, params: Dict[str, Any]) -> Any:
        pass

    @staticmethod
    async def run_with_retry(max_retries: int, func: Callable, **kwargs) -> Tuple[ErrorBody, Any]:
        max_attempts = max_retries + 1
        result: Any = {}
        error_body = ErrorBody()

        for attempt in range(max_attempts):
            logger.debug(f"Attempt {attempt + 1}/{max_attempts} to execute code")

            try:
                result = await func(**kwargs)
                break
            except (asyncio.TimeoutError, TimeoutError):
                error_body = ErrorBody(
                    error_message=f"Execution timed out after {attempt + 1}/{max_attempts} attempts",
                    error_code=4001
                )
                logger.error(f"{error_body}")
            except Exception as e:
                error_body = ErrorBody(
                    error_message=f"Execution failed after {attempt + 1}/{max_attempts} attempts: {e}",
                    error_code=4002
                )
                logger.error(f"{error_body}")

        logger.info(f"error_body: {error_body}")
        logger.info(f"result: {result}")
        return error_body, result
