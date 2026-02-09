# openjiuwen.core.memory.config

## class openjiuwen.core.memory.config.SysMemConfig

定义记忆引擎初始化相关的配置参数，控制是否记录消息以及记忆生成的配置。

* ​**record_message**​(bool)：是否记录消息。True表示记录消息，False表示不记录消息，默认值：True。
* ​**ai_msg_gen_mem_max_len**​(int)：表示用于提取记忆的AI消息的最大长度，如果消息太长则不提取。默认值：64，表示如果消息超过64个字符，则不提取记忆。
* ​**history_window_size_to_gen_mem**​(int)：用于生成记忆的历史消息条数，单位：条，默认值：5。
* ​**crypto_key**​(bytes)：aes密钥，长度必须为32，如果为空，则不启用加密内存，默认值: b''。

## class openjiuwen.core.memory.config.MemoryConfig

定义记忆变量和是否开启长期记忆的开关。

* ​**mem_variables**​(dict[str, str])：记忆变量的配置，dict类型，key为变量名，value为变量描述。默认值：无。
* ​**enable_long_term_mem**​(bool)：是否开启长期记忆。True表示开启长期记忆，False表示不开启长期记忆，默认值：True。
