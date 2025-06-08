from sqlmodel import Field, SQLModel


class RembgService(SQLModel, table=True):
    __tablename__ = "ml_onnx_image_table"
    rembg_id: int = Field(default=None, primary_key=True)
    ml_onnx_name: str  # = Field(default=None, primary_key=True)
    ml_onnx: bytes  # = Field(default=None, foreign_key="")
