class DomainError(Exception):
    """Business-rule failure. main.py maps status_code onto the HTTP response."""

    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    status_code = 404


class Forbidden(DomainError):
    status_code = 403


class Conflict(DomainError):
    status_code = 409


class InvalidTransition(Conflict):
    pass


class IdempotencyKeyReused(DomainError):
    status_code = 422
