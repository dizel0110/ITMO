from datetime import datetime
from typing import Optional

from sqlmodel import TIMESTAMP, Column, Field, SQLModel


class Dataimage(SQLModel, table=True):
    __tablename__ = "data_image"
    image_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, foreign_key="user_table.id")
    input_image_path: str
    output_image_path: str
    date: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
