from sqlmodel import Field, SQLModel


class Balance(SQLModel, table=True):
    __tablename__ = "balance_table"
    balance_id: int = Field(default=None, primary_key=True)
    user_id: int = Field(default=None, foreign_key="user_table.id")
    balance: float
