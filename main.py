from internal.config.secret import validate_environment, SecretManager
from internal.config.paths_config import CLIENT_DIR

from server.controller import router

  
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


validate_environment(
    ["SERPER_API_KEY", "GOOGLE_API_KEY", "OPENAI_KEY"]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
  
    yield


app = FastAPI(title="Akwaya - Your Lead Generation Engine", lifespan=lifespan)

app.include_router(router=router)

app.mount(
    "/assets",
    StaticFiles(directory=CLIENT_DIR / "assets"),
    name="assets",
)


@app.get("/")
def homepage():
    """Serve the React app homepage (SPA entry)."""
    return FileResponse(CLIENT_DIR / "index.html")


@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """SPA fallback: serve index.html for client-side routes."""
    return FileResponse(CLIENT_DIR / "index.html")


app.add_middleware(
    CORSMiddleware,
    allow_origins=SecretManager.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(SecretManager.PORT),
        log_level="debug",
        reload=SecretManager.ENV.is_local,
        timeout_graceful_shutdown=30
        
    )
    

