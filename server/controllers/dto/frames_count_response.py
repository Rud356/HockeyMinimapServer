from pydantic import BaseModel

class FramesCountResponse(BaseModel):
    from_frame: int
    to_frame: int
