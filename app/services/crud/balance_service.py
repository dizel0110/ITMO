from typing import List

from common.userservice.balance import Balance
from sqlmodel import update


class BalanceService:

    @classmethod
    def get_all_balance(cls, session) -> List[Balance]:
        return session.query(Balance).all()

    @classmethod
    def check_balance(cls, user_id, session):
        balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        if balance:
            return balance.balance
        else:
            return 'Не удалось проверить баланс. Попробуйте позже.'

    @classmethod
    def init_balance(cls, new_balance: Balance, session):
        session.add(new_balance)
        session.commit()
        session.refresh(new_balance)

    @classmethod
    def check_balance_sufficiency(cls, user_id, session):
        user_id_balance = (
            session.query(Balance).filter(Balance.user_id == user_id).first()
        )
        if user_id_balance.balance > 50:
            return user_id_balance.balance
        else:
            return False

    @classmethod
    def balance_up(cls, user_id, balance_add, session):
        balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        new_balance = balance.balance + balance_add
        balance_upd = (
            update(Balance)
            .where(Balance.user_id == user_id)
            .values(balance=new_balance)
        )
        session.execute(balance_upd)
        session.commit()

    @classmethod
    def balance_down(cls, user_id, price, session):
        balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        new_balance = balance.balance - price
        balance_upd = (
            update(Balance)
            .where(Balance.user_id == user_id)
            .values(balance=new_balance)
        )
        session.execute(balance_upd)
        session.commit()
