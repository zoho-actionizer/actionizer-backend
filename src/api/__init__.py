from fastapi import FastAPI
from .routes import router

app = FastAPI(title="Actionizer - Contextual Action Engine for *cliq*")

app.include_router(router)
