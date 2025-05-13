from pydantic import BaseModel


class SubsetCreatedResponse(BaseModel):
    dataset_id: int
    subset_id: int
