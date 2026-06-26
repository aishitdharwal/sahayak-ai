from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.db.session import TicketRecord, AuditRecord
from backend.models.audit import AuditLogEntry


def create_ticket(db: Session, ticket_id: str, customer_name: str,
                  customer_email: str, order_id: str, raw_text: str):
    existing = db.query(TicketRecord).filter(TicketRecord.ticket_id == ticket_id).first()
    if existing:
        return existing
    record = TicketRecord(
        ticket_id=ticket_id,
        customer_name=customer_name,
        customer_email=customer_email,
        order_id=order_id,
        raw_text=raw_text,
        status="pending",
    )
    db.add(record)
    db.commit()
    return record


def update_ticket_status(db: Session, ticket_id: str, status: str):
    record = db.query(TicketRecord).filter(TicketRecord.ticket_id == ticket_id).first()
    if record:
        record.status = status
        db.commit()


def get_tickets_by_status(db: Session, status: str):
    return db.query(TicketRecord).filter(TicketRecord.status == status).all()


def save_audit_log(db: Session, entry: AuditLogEntry):
    record = AuditRecord(**entry.model_dump())
    db.add(record)
    db.commit()
    return record
