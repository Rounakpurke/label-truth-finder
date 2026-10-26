class ApiError(Exception):
    """An error whose message is safe to show to the browser."""

    def __init__(self, message, code="error", status=500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
