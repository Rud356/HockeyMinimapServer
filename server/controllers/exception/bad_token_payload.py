from .unauthorized_resource_access import UnauthorizedResourceAccess


class BadTokenPayload(UnauthorizedResourceAccess):
    def __init__(self):
        super().__init__("Bad authorization token")
