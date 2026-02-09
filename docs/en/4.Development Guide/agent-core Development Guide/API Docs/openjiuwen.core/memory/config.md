# openjiuwen.core.memory.config

## class openjiuwen.core.memory.config.SysMemConfig

Defines configuration parameters for initializing the memory engine, controlling whether messages are recorded and how memories are generated.

- **record_message** (bool): Whether to record messages. True means messages are recorded; False means they are not. Default: True.
- **ai_msg_gen_mem_max_len** (int): Maximum length of an AI message eligible for memory extraction. If a message exceeds this length, no memory is extracted. Default: 64 (messages longer than 64 characters are ignored for memory extraction).
- **history_window_size_to_gen_mem** (int): Number of historical messages to consider when generating memory. Default: 5.
- **crypto_key** (bytes): AES key; must be 32 bytes long. If empty, encrypted memory is disabled. Default: b''.

## class openjiuwen.core.memory.config.MemoryConfig

Defines memory variables and the switch for enabling long-term memory.

- **mem_variables** (dict[str, str]): Configuration of memory variables. Keys are variable names; values are descriptions. Default: None.
- **enable_long_term_mem** (bool): Whether to enable long-term memory. True enables it; False disables it. Default: True.