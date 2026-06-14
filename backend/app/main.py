import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import text
from .database import engine, Base, SessionLocal
from .routers import auth, config, players, rounds, ranking, financial, import_round
from .seed import seed_db

FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

ENV = os.getenv("ENV", "development")
IS_PROD = ENV == "production"

if IS_PROD:
    render_url = os.getenv("RENDER_EXTERNAL_URL", "")
    ALLOWED_ORIGINS = [render_url] if render_url else []
else:
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Poker Night Manager API",
    version="1.0.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api"
app.include_router(auth.router,      prefix=API)
app.include_router(config.router,    prefix=API)
app.include_router(players.router,   prefix=API)
app.include_router(rounds.router,    prefix=API)
app.include_router(ranking.router,   prefix=API)
app.include_router(financial.router,     prefix=API)
app.include_router(import_round.router, prefix=API)


@app.on_event("startup")
def startup():
    # Migrate existing SQLite DBs: add new columns if missing
    if engine.url.get_dialect().name == "sqlite":
        with engine.connect() as conn:
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(players)"))}
            if "telefone" not in cols:
                conn.execute(text("ALTER TABLE players ADD COLUMN telefone VARCHAR"))
            if "pix" not in cols:
                conn.execute(text("ALTER TABLE players ADD COLUMN pix VARCHAR"))

            rp_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(round_players)"))}
            if "colocacao" not in rp_cols:
                conn.execute(text("ALTER TABLE round_players ADD COLUMN colocacao INTEGER DEFAULT 0"))

            cfg_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(config)"))}
            if "pix_receiver_player_id" not in cfg_cols:
                conn.execute(text("ALTER TABLE config ADD COLUMN pix_receiver_player_id INTEGER"))
            conn.commit()

    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()


@app.get("/health", tags=["Health"], summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    if FRONTEND_DIST.exists():
        file = FRONTEND_DIST / full_path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")
    return {"status": "ok"}
