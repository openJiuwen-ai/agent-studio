from jiuwen.orchestration.callbacks.manager import CallbackHandlerManager


def init_long_memory():
    from .global_vals_callback_handler import GlobalVals4CallbackHandler
    CallbackHandlerManager().add_handler(GlobalVals4CallbackHandler())
