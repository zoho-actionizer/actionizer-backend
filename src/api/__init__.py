from fastapi import FastAPI
from .routes import router
from . import auth

app = FastAPI(title="Actionizer - Contextual Action Engine for *cliq*")

app.include_router(router)
app.include_router(auth.router)
