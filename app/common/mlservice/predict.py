import onnxruntime as ort
from sqlmodel import Field, SQLModel

model_path = "./model/u2net.onnx"
session = ort.InferenceSession(model_path)
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

class MyModel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    image_data: bytes = Field(nullable=False)

    def predict(self, input_image):
        inputs = {input_name: input_image}
        outputs = session.run([output_name], inputs)
        return outputs[0]
