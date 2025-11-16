"""API endpoints for run logs."""

import json
import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.run_log_repository import RunLogRepository
from app.repositories.run_repository import RunRepository
from app.schemas.run_log import (
    RunLog,
    RunLogCreate,
    RunLogBatchCreate,
    RunLogList,
    RunLogFilter,
)

router = APIRouter()


# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections for log streaming."""

    def __init__(self):
        self.active_connections: dict[UUID, List[WebSocket]] = {}

    async def connect(self, run_id: UUID, websocket: WebSocket):
        """Connect a websocket for a run."""
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

    def disconnect(self, run_id: UUID, websocket: WebSocket):
        """Disconnect a websocket."""
        if run_id in self.active_connections:
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: UUID, message: dict):
        """Broadcast a message to all connected clients for a run."""
        if run_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[run_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)

            # Clean up disconnected websockets
            for websocket in disconnected:
                self.disconnect(run_id, websocket)


manager = ConnectionManager()


@router.post("/{run_id}/logs", response_model=RunLog, status_code=status.HTTP_201_CREATED)
async def create_log(
    run_id: UUID,
    log_data: RunLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a single run log.

    Args:
        run_id: Run ID
        log_data: Log data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created run log
    """
    # TODO: Check if user has access to the run

    repo = RunLogRepository(db)
    run_log = repo.create(run_id, log_data)

    # Broadcast to WebSocket clients
    await manager.broadcast(
        run_id,
        {
            "id": str(run_log.id),
            "level": run_log.level,
            "message": run_log.message,
            "timestamp": run_log.timestamp.isoformat(),
            "source": run_log.source,
            "line_number": run_log.line_number,
        }
    )

    return run_log


@router.post("/{run_id}/logs/batch", status_code=status.HTTP_201_CREATED)
async def create_logs_batch(
    run_id: UUID,
    batch_data: RunLogBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch create run logs.

    Args:
        run_id: Run ID
        batch_data: Batch of logs
        db: Database session
        current_user: Current authenticated user

    Returns:
        Number of logs created
    """
    # TODO: Check if user has access to the run

    repo = RunLogRepository(db)
    logs = repo.create_batch(run_id, batch_data.logs)

    # Broadcast to WebSocket clients
    for log in logs:
        await manager.broadcast(
            run_id,
            {
                "id": str(log.id),
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat(),
                "source": log.source,
                "line_number": log.line_number,
            }
        )

    return {"created": len(logs)}


@router.get("/{run_id}/logs", response_model=RunLogList)
def list_logs(
    run_id: UUID,
    level: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all logs for a run with optional filtering.

    Args:
        run_id: Run ID
        level: Filter by log level
        source: Filter by source
        search: Search in message
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of logs
    """
    # TODO: Check if user has access to the run

    filter_params = RunLogFilter(
        level=level,
        source=source,
        search=search,
    )

    repo = RunLogRepository(db)
    logs, total = repo.list_by_run(run_id, filter_params=filter_params, skip=skip, limit=limit)

    return RunLogList(
        items=logs,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{run_id}/logs/latest", response_model=List[RunLog])
def get_latest_logs(
    run_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest logs for a run.

    Args:
        run_id: Run ID
        limit: Maximum number of logs to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of latest logs
    """
    # TODO: Check if user has access to the run

    repo = RunLogRepository(db)
    logs = repo.get_latest_logs(run_id, limit=limit)
    return logs


@router.get("/{run_id}/logs/summary")
def get_logs_summary(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary of logs for a run.

    Args:
        run_id: Run ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Summary of logs by level
    """
    # TODO: Check if user has access to the run

    repo = RunLogRepository(db)
    summary = repo.get_log_levels_summary(run_id)
    total = repo.get_log_count_by_run(run_id)

    return {
        "total": total,
        "by_level": summary
    }


@router.get("/{run_id}/logs/download")
def download_logs(
    run_id: UUID,
    format: str = "txt",
    level: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download logs for a run.

    Args:
        run_id: Run ID
        format: Download format (txt, json, csv)
        level: Filter by log level
        source: Filter by source
        search: Search in message
        db: Database session
        current_user: Current authenticated user

    Returns:
        Log file download
    """
    # TODO: Check if user has access to the run

    filter_params = RunLogFilter(
        level=level,
        source=source,
        search=search,
    )

    repo = RunLogRepository(db)
    logs, _ = repo.list_by_run(run_id, filter_params=filter_params, skip=0, limit=100000)

    if format == "json":
        content = json.dumps([
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "source": log.source,
                "message": log.message,
                "line_number": log.line_number,
            }
            for log in logs
        ], indent=2)
        media_type = "application/json"
        filename = f"run_{run_id}_logs.json"

    elif format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Level", "Source", "Line", "Message"])
        for log in logs:
            writer.writerow([
                log.timestamp.isoformat(),
                log.level,
                log.source,
                log.line_number or "",
                log.message
            ])
        content = output.getvalue()
        media_type = "text/csv"
        filename = f"run_{run_id}_logs.csv"

    else:  # txt
        lines = []
        for log in logs:
            timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"[{timestamp}] [{log.level}] [{log.source}] {log.message}")
        content = "\n".join(lines)
        media_type = "text/plain"
        filename = f"run_{run_id}_logs.txt"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.websocket("/{run_id}/logs/stream")
async def stream_logs(
    websocket: WebSocket,
    run_id: UUID,
    db: Session = Depends(get_db),
):
    """Stream logs via WebSocket.

    Args:
        websocket: WebSocket connection
        run_id: Run ID
        db: Database session
    """
    await manager.connect(run_id, websocket)

    try:
        # Send existing logs first
        repo = RunLogRepository(db)
        existing_logs = repo.get_latest_logs(run_id, limit=100)

        for log in existing_logs:
            await websocket.send_json({
                "id": str(log.id),
                "level": log.level,
                "message": log.message,
                "timestamp": log.timestamp.isoformat(),
                "source": log.source,
                "line_number": log.line_number,
            })

        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            # Client can send "ping" to keep connection alive
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(run_id, websocket)


@router.delete("/{run_id}/logs", status_code=status.HTTP_204_NO_CONTENT)
def delete_logs(
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all logs for a run.

    Args:
        run_id: Run ID
        db: Database session
        current_user: Current authenticated user
    """
    # TODO: Check if user has access to the run

    repo = RunLogRepository(db)
    repo.delete_by_run(run_id)
