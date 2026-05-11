from nb_log import LogManager

# 获取一个 nb_log 的 logger
logger = LogManager('test').get_logger_and_add_handlers(
    is_add_stream_handler=True,
    log_filename='test.log',
    log_file_size=30,
    log_file_handler_type=2
)