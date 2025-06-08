from typing import List, Optional, Any

from models.user import User


def get_all_users(session) -> List[User]:
    return session.query(User).all()


def get_user_by_id(user_id: int, session) -> Optional[User]:
    user = session.query(User).filter(User.id == user_id).first()
    if user:
        return user
    return None


def get_user_by_email(email: str, session) -> Optional[User]:
    user = session.query(User).filter(User.email == email).first()
    if user:
        return user
    return None


def create_user(new_user: User, session) -> None:
    session.add(new_user)
    session.commit()
    session.refresh(new_user)


def get_user_autorization(email: str, password: str, session) -> Optional[Any]:
    user = session.query(User).filter(User.email == email).first()
    if user and user.password == password:
        return True
    return False


