#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
This module defines a global singleton ComponentClassPool to manage custom component classes.
"""

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.utils.singleton import Singleton
from jiuwen.orchestration.flow.constant import BUILT_IN_COMPONENT_PREFIX


class ComponentClassPool(metaclass=Singleton):
    """
    Defines a Singleton ComponentClassPool to manage custom component classes.
    """

    def __init__(self):
        self._pool = {}
        # 自定义组件定义
        self.custom_component_hci = set()

    def register_component_class(self, comp_type: str, cls: type):
        """
        Register a component class to the component class pool.

        :param comp_type: The type of the component.
            Needs to be unique and cannot use the prefix for built-in component types.
        :param cls: The class object of the component.
        """
        if not isinstance(cls, type):
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_POOL_REGISTER_TYPE_ERROR.code,
                message=StatusCode.COMPONENT_POOL_REGISTER_TYPE_ERROR.errmsg,
            )
        if (
            comp_type.startswith(BUILT_IN_COMPONENT_PREFIX)
            and "jiuwen.code" not in comp_type
            and "jiuwen.templateTransform" not in comp_type
        ):
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_POOL_REGISTER_INVALID_CLASS_NAME.code,
                message=StatusCode.COMPONENT_POOL_REGISTER_INVALID_CLASS_NAME.errmsg.format(
                    comp_type=comp_type,
                    err_msg=f"Custom component class type should avoid using the prefix '{BUILT_IN_COMPONENT_PREFIX}'",
                ),
            )
        self._pool[comp_type] = cls

    def get_component_class(self, comp_type: str):
        """
        Get the class object of a component from the component pool.

        :param comp_type: The type of the component.
        :return: The class object of the component.
        """
        cls = self._pool.get(comp_type)
        if cls is None:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_POOL_GET_CLASS_ERROR.code,
                message=StatusCode.COMPONENT_POOL_GET_CLASS_ERROR.errmsg.format(
                    comp_type=comp_type
                ),
            )
        return cls

    def create_component_instance(self, comp_type: str, *args, **kwargs):
        """
        Create an instance of a component from the component pool.

        :param comp_type: The type of the component.
        :param args: Positional arguments for the constructor.
        :param kwargs: Keyword arguments for the constructor.
        :return: An instance of the component.
        """
        cls = self._pool.get(comp_type)
        if cls is None:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_POOL_GET_CLASS_ERROR.code,
                message=StatusCode.COMPONENT_POOL_GET_CLASS_ERROR.errmsg.format(
                    comp_type=comp_type
                ),
            )
        try:
            instance = cls(*args, **kwargs)
        except JiuWenBaseException:
            raise
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_POOL_INSTANTIATION_ERROR.code,
                message=StatusCode.COMPONENT_POOL_INSTANTIATION_ERROR.errmsg.format(
                    comp_type=comp_type
                ),
            ) from e
        if hasattr(instance, "node_state"):
            self.custom_component_hci.add(comp_type)
        return instance


component_class_pool = ComponentClassPool()
