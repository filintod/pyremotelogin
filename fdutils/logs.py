import logging
from contextlib import contextmanager


@contextmanager
def temp_file_logging_handler(logging_filepath, redirect_from_root=False):
    """ temporarily create another logger to where to send logging info to (the default is still also used)

    Args:
        logging_filepath:

    Returns:

    """
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    file_handler = logging.FileHandler(logging_filepath, mode='w')
    file_handler.setFormatter(formatter)

    if not redirect_from_root:
        logging.root.addHandler(file_handler)
        yield
        logging.root.removeHandler(file_handler)
    else:
        logging.getLogger(__name__).info('\n{div}\n   LOGGING IS BEING REDIRECTED TO {redirect}\n{div}\n'
                                         ''.format(div='#' * 80, redirect=logging_filepath))

        root_stream = logging.root.handlers[0].stream
        logging._acquireLock()
        try:
            logging.root.handlers[0].stream = file_handler.stream
            yield
            file_handler.close()
        finally:
            logging._releaseLock()
            logging.root.handlers[0].stream = root_stream


def init_logging(log_file_path='logging.log', logger_level=logging.DEBUG,
                 logging_to_console=True, logging_to_console_level=logging.ERROR,
                 file_format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                 console_format='%(name)-12s: %(levelname)-8s %(message)s',
                 date_format='%m-%d %H:%M:%S', max_message_length=0):
    """ Initializes the logging level and set it to output to file and console with the logging level of the file set by logger_level

    Args:
        log_file_path: folder where to store the log file
        logger_level: default file log level
        logging_to_console: whether to log to console or not
        logging_to_console_level: console log level
        file_format (str): format for file (https://docs.python.org/3/howto/logging-cookbook.html#formatting-styles)
        console_format (str): format for console
        date_format (str): format for datetime

    """

    # remove previous handlers in case we are running back to back _tests
    while len(logging.root.handlers) > 0:
        logging.root.removeHandler(logging.root.handlers[-1])

    logging.basicConfig(level=logger_level,
                        format=file_format,
                        datefmt=date_format,
                        filename=log_file_path,
                        filemode='w')

    if logging_to_console:
        console = logging.StreamHandler()
        console.setLevel(logging_to_console_level)
        formatter = logging.Formatter(console_format)
        console.setFormatter(formatter)
        logging.root.addHandler(console)

    if max_message_length:
        def set_logging_limit(l):
            old_factory = l.getLogRecordFactory()

            def record_factory(*args, **kwargs):
                record = old_factory(*args, **kwargs)
                len_record = len(record.msg)
                if len_record > max_message_length:
                    remaining = len_record - max_message_length
                    record.msg = record.msg[:max_message_length] + \
                                 "\n ---- message truncated (remaining chars {}) ----".format(remaining)
                return record

            l.setLogRecordFactory(record_factory)

        set_logging_limit(logging)
        if logging_to_console:
            set_logging_limit(console)
