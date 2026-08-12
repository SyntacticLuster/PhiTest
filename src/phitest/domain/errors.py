class PhiTestError(Exception):
    """Base application error."""


class NotFoundError(PhiTestError):
    pass


class ValidationError(PhiTestError):
    pass


class ImmutabilityError(PhiTestError):
    pass


class AdapterError(PhiTestError):
    pass


class ProtocolError(PhiTestError):
    pass


class OversizedResponseError(AdapterError):
    pass
