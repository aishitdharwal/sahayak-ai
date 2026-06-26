from sqlalchemy import create_engine, Column, String, Float, Boolean, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from backend.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # SQLite only
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TicketRecord(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String, primary_key=True)
    customer_name = Column(String)
    customer_email = Column(String)
    order_id = Column(String)
    raw_text = Column(Text)
    status = Column(String, default="pending")  # pending | awaiting_hitl | completed | rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class AuditRecord(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True)
    ticket_id = Column(String)
    order_id = Column(String)
    issue_type = Column(String)
    ai_draft = Column(Text)
    human_final = Column(Text)
    hitl_action = Column(String)
    human_agent_id = Column(String)
    sop_citation = Column(String)
    was_edited = Column(Boolean)
    edit_diff_chars = Column(Integer)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
