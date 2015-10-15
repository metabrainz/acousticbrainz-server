class APIError(Exception):

    def __init__(self, message, status_code, payload=None):
        super(APIError, self).__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class APINotFound(APIError):
    def __init__(self, message, payload=None):
        super(APINotFound, self).__init__(message, 404, payload)

class APIBadRequest(APIError):
    def __init__(self, message, payload=None):
        super(APIBadRequest, self).__init__(message, 400, payload)
