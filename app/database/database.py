from sqlmodel import Session, SQLModel, create_engine
from common.mlservice.rembg_service import RembgService

from .config import get_settings

engine = create_engine(
    url=get_settings().DATABASE_URL_psycopg, echo=True, pool_size=5, max_overflow=10
)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    unet_model_name = 'u2net.onnx'
    with open('./common/mlservice/model/' + unet_model_name, 'rb') as file:
        used_model = file.read()
    unet_model = RembgService(
        ml_onnx_name=unet_model_name,
        ml_onnx=used_model,
    )
    with Session(engine) as session:
        session.add(unet_model)
        session.commit()
