class DomainError(Exception):
    """Base domain/application error with a user-facing message."""


class ValidationError(DomainError):
    pass


class AlreadyExists(DomainError):
    pass


class NotFound(DomainError):
    pass


class ArchivedEntity(DomainError):
    pass


class InUse(DomainError):
    pass
