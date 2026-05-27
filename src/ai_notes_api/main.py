from fastapi import FastAPI

from ai_notes_api.api.v1 import router

app = FastAPI(
    title="AI Note's API",
    version="0.1.0",
)

app.include_router(router)
