from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from database.database import get_session, engine, init_db
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from models.user import TokenResponse, User
from services.crud import user as UserService
from typing import List
from common.userservice.balance import Balance
from services.crud.balance_service import BalanceService

user_router = APIRouter(tags=["Users"])
hash_password = HashPassword()


@user_router.post("/signup")
async def registration(user_data: User, session=Depends(get_session)):
    user_exists = UserService.get_user_by_email(user_data.email, session)

    if user_exists:
        return status.HTTP_400_BAD_REQUEST

    hashed_password = hash_password.create_hash(user_data.password)
    user_data.password = hashed_password
    UserService.create_user(user_data, session)
    user_data = UserService.get_user_by_id(user_data.id, session)
    balance_user_exists = Balance(
        user_id=user_data.id,
        balance=user_data.credit_amount,
    )
    BalanceService.init_balance(
        balance_user_exists,
        session,
    )
    return {'message': 'User created!'}


@user_router.post("/signin", response_model=TokenResponse)
async def signin(user: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)) -> dict:
    user_exist = UserService.get_user_by_email(user.username, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")

    if hash_password.verify_hash(user.password, user_exist.password):
        access_token = create_access_token(user_exist.email)
        return {"access_token": access_token, "token_type": "Bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )

@user_router.get("/balance/{id}")
async def check_balance(user_id_balance: int, session=Depends(get_session)):
    user = UserService.get_user_by_id(user_id_balance, session)
    balance_checker = BalanceService()
    if not user:
        return {'message': 'User not found'}
    return balance_checker.check_balance(user_id_balance, session)

@user_router.get("/email/{email}")
async def get_user_by_email(email: str, session=Depends(get_session)):
    user = UserService.get_user_by_email(email, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким email не зарегистрирован",
        )
    return user

@user_router.get('/all_users', response_model=List[User])
async def get_all_users(session=Depends(get_session)) -> list:
    return UserService.get_all_users(session)
