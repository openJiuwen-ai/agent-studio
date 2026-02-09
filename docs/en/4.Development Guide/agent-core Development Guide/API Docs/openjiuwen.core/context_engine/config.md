# openjiuwen.core.context_engine.config

## class openjiuwen.core.context_engine.config.ContextEngineConfig
```python
class openjiuwen.core.context_engine.config.ContextEngineConfig()
```
Represents the complete configuration structure for the context engine, used to control various behaviors and parameters of the context engine.

**Parameters**:
- **conversation_history_length**(int, optional): The length of the conversation history, controlling how many conversation messages are retained. Must be greater than or equal to 0. Default: 100.