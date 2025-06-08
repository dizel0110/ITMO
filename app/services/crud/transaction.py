from datetime import datetime

from loguru import logger
from models.transcaction import Transaction
from models.user import User
from services.crud.user import get_user_by_id
from sqlmodel import Session
from database.database import engine, init_db
from fastapi import HTTPException, status

from common.userservice.balance import Balance


class TransactionBusiness:
    @classmethod
    def load_history(cls,  user_id, session, limit: int = 10):
        transactions = (
            session.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.date.desc())
            .limit(limit)
            .all()
        )
        if transactions:
            return transactions
        else:
            return False

    @classmethod
    def add_transaction(
        cls,
        session,
        user_id,
        replenishment=0,
        withdrawal=0,
    ):
        new_transaction = Transaction(
            user_id=user_id,
            date=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            replenishment=replenishment,
            withdrawal=withdrawal,
        )
        session.add(new_transaction)
        session.commit()

    @classmethod
    def replenishment(cls, session, user_id, value):
        user_data = get_user_by_id(user_id, session)
        logger.info(f"Текущий бонусный баланс: {user_data.credit_amount}")

        user_data.credit_amount = user_data.credit_amount + value
        user_balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        if user_balance:
            user_balance.balance = user_data.credit_amount
            session.add(user_balance)
            session.commit()
        else:
            user_balance = Balance(
                user_id=user_id,
                balance=user_data.credit_amount,
            )
            session.add(user_balance)
            session.commit()
        logger.info(
            f"Пополнение бонусного баланса на {value}. Текущий бонусный баланс: {user_data.credit_amount}"
        )
        session.add(user_data)
        session.commit()
        cls.add_transaction(session, user_id=user_id, replenishment=value)



    @classmethod
    def withdrawal(cls, session, user_id, value):
        user_data = get_user_by_id(user_id, session)
        logger.info(f"Текущий бонусный баланс: {user_data.credit_amount}")
        user_balance = session.query(Balance).filter(Balance.user_id == user_id).first()
        if not user_balance:
            user_balance = Balance(
                user_id=user_id,
                balance=user_data.credit_amount,
            )
        if user_data.credit_amount - value >= 0:
            user_data.credit_amount -= value
            user_balance.balance = user_data.credit_amount
            session.add(user_balance)
            session.commit()
            logger.info(
                f"Списание с бонусного баланса на {value}. Текущий бонусный баланс: {user_data.credit_amount}"
            )
            session.add(user_data)
            session.commit()
            cls.add_transaction(session, user_id=user_id, withdrawal=value)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Insufficient funds. Balance: {user_data.credit_amount}'
            )

    @classmethod
    def del_transaction(cls, session, user_id):
        result = session.query(Transaction).filter(Transaction.user_id == user_id).all()
        for obj in result:
            session.delete(obj)
        session.commit()
        logger.info(f"История транзакций пользователя с id{user_id} удалена из базы")
