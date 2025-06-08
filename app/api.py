from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routes.ml import bgremover_router
from routes.transactions import transactions_router
from routes.users import user_router

from database.database import init_db

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
async def home():
    return RedirectResponse(url="/docs")


app.include_router(bgremover_router, prefix="/rembg")
app.include_router(transactions_router, prefix="/transaction")
app.include_router(user_router, prefix="/user")


if __name__ == "__main__":
    print("App started. To exit, press Ctrl+C.")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
