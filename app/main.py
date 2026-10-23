import contextvars
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import build_engine, get_session
from app.models import Task
from app.schemas import TaskRead, TaskWrite

logger = logging.getLogger(__name__)
request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
SessionDependency = Annotated[Session, Depends(get_session)]
TaskId = Annotated[int, Path(gt=0, le=2147483647)]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        for field in ("method", "path", "status_code", "duration_ms", "error_type"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        config = settings or get_settings()
        configure_logging(config.log_level)
        engine = build_engine(config.database_url.get_secret_value())
        application.state.engine = engine
        try:
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Cloud Deployment Platform", lifespan=lifespan)

    @application.middleware("http")
    async def log_request(request: Request, call_next):
        supplied_id = request.headers.get("X-Request-ID", "")
        valid_id = re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_id)
        request_id = supplied_id if valid_id else uuid4().hex
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logger.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_context.reset(token)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Do not echo request bodies or rejected values, which may contain secrets.
        errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @application.exception_handler(SQLAlchemyError)
    async def database_failure(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # Exception strings and tracebacks can contain SQL or connection details.
        logger.error("database_operation_failed", extra={"error_type": type(exc).__name__})
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/ready")
    def ready(session: SessionDependency) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ready"}

    @application.get("/tasks", response_model=list[TaskRead])
    def list_tasks(session: SessionDependency) -> list[Task]:
        return list(session.scalars(select(Task).order_by(Task.id)))

    def find_task(task_id: int, session: Session) -> Task:
        task = session.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @application.get("/tasks/{task_id}", response_model=TaskRead)
    def read_task(task_id: TaskId, session: SessionDependency) -> Task:
        return find_task(task_id, session)

    @application.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskWrite, session: SessionDependency, response: Response) -> Task:
        task = Task(**payload.model_dump())
        session.add(task)
        session.commit()
        session.refresh(task)
        response.headers["Location"] = f"/tasks/{task.id}"
        return task

    @application.put("/tasks/{task_id}", response_model=TaskRead)
    def update_task(task_id: TaskId, payload: TaskWrite, session: SessionDependency) -> Task:
        task = find_task(task_id, session)
        for name, value in payload.model_dump().items():
            setattr(task, name, value)
        session.commit()
        session.refresh(task)
        return task

    @application.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(task_id: TaskId, session: SessionDependency) -> Response:
        session.delete(find_task(task_id, session))
        session.commit()
        return Response(status_code=204)

    return application


app = create_app()
