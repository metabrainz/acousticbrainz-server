class NoDataFoundException(Exception):
    """Should be used when no data has been found."""
    pass

class BadDataException(Exception):
    """Should be used when incorrect data is being submitted."""
    pass
