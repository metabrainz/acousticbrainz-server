class MBDatabaseException(Exception):
    """Base exception for all exceptions related to MusicBrainz database"""
    pass

class NoDataFoundException(MBDatabaseException):
    """Exception to be raised when no data has been found"""
    pass
