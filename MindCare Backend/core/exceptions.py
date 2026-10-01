"""
Shared exception types.

DomainValidationError is what services raise when a business rule rejects
input. Views translate it into a DRF ValidationError (400) so every app
renders rule violations the same way. A project-wide DRF exception handler
may be added here later.
"""


class DomainValidationError(Exception):
    """A business rule rejected the input. `errors` maps field name -> messages."""

    default_code = "invalid"

    def __init__(self, errors, *, code=None):
        super().__init__(errors)
        self.errors = errors
        self.code = code or self.default_code
