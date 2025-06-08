import os

import joblib
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Поставим флаги: приложение готово, но модель не подгружена
is_alive = True
is_ready = False

try:
    os.system("dvc pull ./model/model.pkl.dvc")
    model = joblib.load("model/model.pkl")
    is_ready = True

except FileNotFoundError:
    model = None
    reason = "File not found"
except Exception as e1:
    model = None
    reason = "An error occurred while loading the model:" + str(e1)


class WineParams(BaseModel):
    fixed_acidity: float
    volatile_acidity: float
    citric_acid: float
    residual_sugar: float
    chlorides: float
    free_sulfur_dioxide: float
    total_sulfur_dioxide: float
    density: float
    pH: float
    sulphates: float
    alcohol: float


@app.post("/predict/")
def predict_quality(parameters: WineParams):
    features_df = pd.DataFrame([parameters.dict()])
    features_df.columns = features_df.columns.str.replace("_", " ")
    prediction = model.predict(features_df)
    return {"predicted_quality": float(prediction[0])}


@app.get("/liveness")
def liveness():
    if is_alive:
        return {"status": "ok"}
    raise HTTPException(status_code=503, detail="service is not alive")


@app.get("/readiness")
def readiness():
    if is_ready:
        return {"status": "ok"}
    raise HTTPException(status_code=503, detail="service is not ready")


@app.get("/healthcheck")
def health_check():
    global model
    try:
        if (
            model is not None
            and hasattr(model, "n_features_in_")
            and model.n_features_in_ > 0
        ):
            return {"status": "ok"}
        else:
            return {"status": "error", "reason": "model"}
    except Exception:
        return {"status": "error", "reason": "unknown"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
