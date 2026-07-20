from typing import Any, Dict, List, Optional

from app.repositories.db import get_connection


def create_commitment(extraction: Dict[str, Any], source_channel: Optional[str] = None) -> int:
    conn = get_connection()
    actor = extraction.get("actor") or {}
    cur = conn.execute(
        """
        INSERT INTO commitments
        (task_title, actor_type, actor_name, beneficiary, due_at, due_text,
         confidence, source_evidence, source_channel, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'staged')
        """,
        (
            extraction.get("task_title", ""),
            actor.get("type"),
            actor.get("name"),
            extraction.get("beneficiary"),
            extraction.get("due_at"),
            extraction.get("due_text", ""),
            extraction.get("confidence", 0.0),
            extraction.get("source_evidence", ""),
            source_channel,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def list_commitments(status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM commitments WHERE status = ? ORDER BY id DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM commitments ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_commitment(commitment_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM commitments WHERE id = ?", (commitment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_status(commitment_id: int, status: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    conn.execute("UPDATE commitments SET status = ? WHERE id = ?", (status, commitment_id))
    conn.commit()
    row = conn.execute("SELECT * FROM commitments WHERE id = ?", (commitment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def edit_commitment(commitment_id: int, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    allowed = {"task_title", "due_at", "due_text", "beneficiary"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return get_commitment(commitment_id)
    conn = get_connection()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE commitments SET {set_clause} WHERE id = ?",
        (*updates.values(), commitment_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM commitments WHERE id = ?", (commitment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def export_to_xlsx(status: "str | None" = None) -> bytes:
    """Build an .xlsx workbook of commitments and return it as raw bytes."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font

    rows = list_commitments(status)

    wb = Workbook()
    ws = wb.active
    ws.title = "Commitments"

    headers = [
        "ID", "Task", "Actor Type", "Actor Name", "Beneficiary",
        "Due At", "Due Text", "Confidence", "Source Evidence",
        "Source Channel", "Status", "Created At",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in rows:
        ws.append([
            r.get("id"),
            r.get("task_title"),
            r.get("actor_type"),
            r.get("actor_name"),
            r.get("beneficiary"),
            r.get("due_at"),
            r.get("due_text"),
            r.get("confidence"),
            r.get("source_evidence"),
            r.get("source_channel"),
            r.get("status"),
            r.get("created_at"),
        ])

    for col_cells in ws.columns:
        max_len = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
