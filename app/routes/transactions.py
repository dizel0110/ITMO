from database.database import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from services.crud import transaction as TransactionService

transactions_router = APIRouter(tags=["Transactions"])


@transactions_router.post("/replenishment/{id}")
async def replenishment(user_id: int, amount_up: int, session=Depends(get_session)):
    try:
        transaction_up = TransactionService.TransactionBusiness()
        transaction_up.replenishment(session, user_id=user_id, value=amount_up)
        return "Баланс пополнен"
    except Exception as exc:
        return f"В настоящий момент пополнение не доступно: {exc}"


@transactions_router.post("/withdrawal/{id}")
def withdrawal(user_id: int, amount_down: int, session=Depends(get_session)):
    try:
        transaction_down = TransactionService.TransactionBusiness()
        transaction_down.withdrawal(session, user_id=user_id, value=amount_down)
        return "C баланса списано"
    except Exception as exc:
        return f"В настоящий момент списание не доступно: {exc}"


@transactions_router.get("/history/{id}")
async def show_transaction(user_id: int, session=Depends(get_session)):
    transaction = TransactionService.TransactionBusiness()
    history = transaction.load_history(user_id, session)
    if history:
        return history
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Нет истории - нет проблем."
        )


@transactions_router.delete("/history/{id}/delete")
async def del_transaction(user_id: int, session=Depends(get_session)):
    transaction = TransactionService.TransactionBusiness()
    try:
        transaction.del_transaction(session, user_id=user_id)
        return "История транзакций пользователя очищена"
    except Exception as exc:
        return f"Удалить историю транзакций не удалось по причине: {exc}"
