from datetime import datetime
from pydantic import BaseModel


class JobCreate(BaseModel):
    url: str


class JobStepOut(BaseModel):
    id: int
    step_order: int
    step_name: str
    display_name: str
    status: str
    detail: str | None = None

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: str
    url: str
    status: str
    product_title: str | None = None
    error_message: str | None = None
    progress_pct: float
    final_video_path: str | None = None
    wechat_moments_copy: str | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[JobStepOut] = []

    model_config = {"from_attributes": True}


class JobListOut(BaseModel):
    id: str
    url: str
    status: str
    product_title: str | None = None
    progress_pct: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
