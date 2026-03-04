import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Float, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending/scraping/generating_videos/composing/completed/failed
    product_title = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    progress_pct = Column(Float, default=0.0)
    final_video_path = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    steps = relationship("JobStep", back_populates="job", order_by="JobStep.step_order")


class JobStep(Base):
    __tablename__ = "job_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String, nullable=False)
    display_name = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending/running/completed/failed
    detail = Column(Text, nullable=True)

    job = relationship("Job", back_populates="steps")
