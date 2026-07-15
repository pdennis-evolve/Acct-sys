from flask import g

from app.extensions import db
from app.models.audit import AuditLog


def log_action(entity_type: str, entity_id, action: str, changes: dict | None = None):
    """Append-only audit trail entry. Never call db.session.commit() here —
    callers commit alongside the business-record write in the same transaction."""
    entry = AuditLog(
        tenant_id=g.tenant_id,
        user_id=g.get("user_id"),
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        changes=changes,
    )
    db.session.add(entry)
    return entry
