# memory

`openjiuwen.core.memory` is the memory engine of the openJiuwen framework. It provides capabilities for memory storage, access, and processing during Agent execution.

**Classes**:

| Class | Description                                             |
|---------------------------------------|---------------------------------------------------------|
| [SysMemConfig](./memory/config.md) | System-level configuration class for the memory engine. |
| [MemoryConfig](./memory/config.md) | Group-level configuration class for the memory engine.  |
| [MemoryEngine](./memory/engine.md) | Memory engine class.                                    |
| [BaseKVStore](./memory/store.md) | Abstract base class for key-value store.                |
| [BaseSemanticStore](./memory/store.md) | Abstract base class for semantic store.                 |
| [BaseDbStore](./memory/store.md) | Abstract base class for SQL store.                      |