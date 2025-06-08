from typing import Optional
from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user_table"
    id: int = Field(default=None, primary_key=True)
    email: str
    password: str
    first_name: str
    patronymic: Optional[str]
    last_name: str
    phone: str
    #    created_at:
    login: Optional[str]
    tg_id: int
    credit_amount: Optional[float]
    admin_role: Optional[bool]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserSignIn(SQLModel):
    email: str
    password: str
