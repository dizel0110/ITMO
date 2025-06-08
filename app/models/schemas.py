from pydantic import BaseModel


class UserRegister(BaseModel):
    first_name: str
    patronymic: str
    last_name: str
    #    created_at:
    email: str
    login: str
    password: str
    credit_amount: float
    admin_role: bool
