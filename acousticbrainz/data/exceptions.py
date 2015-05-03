class NoDataFoundException(Exception):
        def __init__(self, message):
            super(NoDataFoundException, self).__init__(message)
