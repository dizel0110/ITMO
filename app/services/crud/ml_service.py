from loguru import logger
from typing import List
from models.data_image import Dataimage


class RembgBusiness:

    def create_note(self, new_dataimage: Dataimage, session) -> None:
        session.add(new_dataimage)
        session.commit()
        session.refresh(new_dataimage)

    def load_history_dataimage(self, user_id, session) -> List[Dataimage]:
        return session.query(Dataimage).filter(Dataimage.user_id == user_id).all()
