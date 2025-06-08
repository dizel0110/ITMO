from datetime import datetime
from typing import List, Optional

from sqlmodel import TIMESTAMP, Column, Field, SQLModel


class Transaction(SQLModel, table=True):
    __tablename__ = "transcaction_table"
    transaction_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, foreign_key="user_table.id")
    date: Optional[datetime] = Field(sa_column=Column(TIMESTAMP(timezone=False)))
    replenishment: Optional[float]
    withdrawal: Optional[float]
    # status_code: str
