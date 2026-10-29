import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import Float, ForeignKey, Integer, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'smartpitch.db'}")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_json: Mapped[str] = mapped_column(String, nullable=False)
    access_token: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("proposals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    block_id: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    time_spent_seconds: Mapped[float] = mapped_column(Float, nullable=False)


class ProposalCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200)]
    company_name: Annotated[str, Field(min_length=1, max_length=200)]
    intro: Annotated[str, Field(min_length=1, max_length=10000)]
    features: Annotated[str, Field(min_length=1, max_length=10000)]
    portfolio: Annotated[str, Field(min_length=1, max_length=10000)]
    pricing: Annotated[str, Field(min_length=1, max_length=10000)]


class TrackRequest(BaseModel):
    token: Annotated[str, Field(min_length=36, max_length=36)]
    block_id: Annotated[str, Field(min_length=1, max_length=80)]
    time_spent_ms: Annotated[int, Field(gt=0, le=86_400_000)]


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SmartPitch", version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/static/dashboard.html")


@app.get("/favicon.ico", include_in_schema=False, status_code=204)
def favicon():
    return Response(status_code=204)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def find_proposal(db: Session, token: str) -> Proposal:
    proposal = db.scalar(select(Proposal).where(Proposal.access_token == token))
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@app.post("/api/proposal/create", status_code=201)
def create_proposal(payload: ProposalCreate, db: Session = Depends(get_db)):
    blocks = [
        {"id": "intro", "title": "The opportunity", "body": payload.intro},
        {"id": "features", "title": "What’s included", "body": payload.features},
        {"id": "portfolio", "title": "Selected work", "body": payload.portfolio},
        {"id": "pricing", "title": "Investment", "body": payload.pricing},
    ]
    proposal = Proposal(
        title=payload.title.strip(),
        company_name=payload.company_name.strip(),
        content_json=json.dumps({"blocks": blocks}, ensure_ascii=False),
        access_token=str(uuid.uuid4()),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return {
        "id": proposal.id,
        "title": proposal.title,
        "company_name": proposal.company_name,
        "access_token": proposal.access_token,
        "share_url": f"/static/viewer.html?token={proposal.access_token}",
    }


@app.get("/api/proposal/{token}")
def get_proposal(token: str, db: Session = Depends(get_db)):
    proposal = find_proposal(db, token)
    try:
        content = json.loads(proposal.content_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Proposal content is invalid") from exc
    return {
        "id": proposal.id,
        "title": proposal.title,
        "company_name": proposal.company_name,
        "blocks": content["blocks"],
    }


@app.post("/api/track", status_code=204)
def track_event(payload: TrackRequest, db: Session = Depends(get_db)):
    proposal = find_proposal(db, payload.token)
    allowed_block_ids = {"intro", "features", "portfolio", "pricing"}
    if payload.block_id not in allowed_block_ids:
        raise HTTPException(status_code=422, detail="Unknown proposal section")
    db.add(
        TrackingEvent(
            proposal_id=proposal.id,
            block_id=payload.block_id,
            time_spent_seconds=payload.time_spent_ms / 1000,
        )
    )
    db.commit()
    return Response(status_code=204)


@app.get("/api/stats/{token}")
def get_stats(token: str, db: Session = Depends(get_db)):
    proposal = find_proposal(db, token)
    rows = db.execute(
        select(
            TrackingEvent.block_id,
            func.sum(TrackingEvent.time_spent_seconds).label("total_seconds"),
            func.count(TrackingEvent.id).label("views"),
        )
        .where(TrackingEvent.proposal_id == proposal.id)
        .group_by(TrackingEvent.block_id)
    ).all()
    totals = {
        row.block_id: {"time_spent_seconds": round(row.total_seconds or 0, 2), "views": row.views}
        for row in rows
    }
    block_ids = ("intro", "features", "portfolio", "pricing")
    return {
        "proposal_id": proposal.id,
        "title": proposal.title,
        "attention": [
            {
                "block_id": block_id,
                "time_spent_seconds": totals.get(block_id, {}).get("time_spent_seconds", 0),
                "views": totals.get(block_id, {}).get("views", 0),
            }
            for block_id in block_ids
        ],
    }


@app.get("/api/proposals")
def list_proposals(db: Session = Depends(get_db)):
    proposals = db.scalars(select(Proposal).order_by(Proposal.id.desc())).all()
    return [
        {
            "id": proposal.id,
            "title": proposal.title,
            "company_name": proposal.company_name,
            "access_token": proposal.access_token,
        }
        for proposal in proposals
    ]


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
