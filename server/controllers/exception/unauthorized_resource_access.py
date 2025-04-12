from fastapi import HTTPException


class UnauthorizedResourceAccess(HTTPException):
    def __init__(
        self,
        message: str = "This resource requires authorization"
    ):
        super().__init__(
            detail=message,
            status_code=401
        )
