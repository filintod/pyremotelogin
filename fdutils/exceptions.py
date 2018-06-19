__author__ = 'Filinto Duran (duranto@gmail.com)'


class RetriesExceededError(Exception):
    def __init__(self, max_val, original_exception):
        msg = "Maximum Number of Retries ({0}) Reached...\n\nException: ".format(max_val, str(original_exception))

        Exception.__init__(self, msg)


class CapabilityError(Exception):
    pass


class ElementNotUniqueError(Exception):
    pass


class ServiceNotFoundError(Exception):
    pass


class FirmwareVersionNotExistError(Exception):
    pass