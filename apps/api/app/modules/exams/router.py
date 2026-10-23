"""Lecturer exam queue, question bank, and draft package routes."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import IdempotencyKey, SuccessEnvelope, request_id, success
from app.api.pagination import require_query_allowlist
from app.db.session import get_session
from app.modules.auth.access import CsrfProtectionDependency
from app.modules.cohorts.router import raise_idempotency_error
from app.modules.exams.access import LecturerActorDependency
from app.modules.exams.schemas import (
    ExamCreate,
    ExamItemsReplace,
    ExamQueueItemResponse,
    ExamResponse,
    ExamUpdate,
    QuestionVersionCreate,
    QuestionVersionResponse,
)
from app.modules.exams.service import (
    ExamConflictError,
    ExamNotFoundError,
    ExamPackageService,
    ExamVersionConflictError,
)
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)

router = APIRouter(tags=["lecturer exams"])


def get_exam_package_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExamPackageService:
    return ExamPackageService(session)


ExamPackageServiceDependency = Annotated[ExamPackageService, Depends(get_exam_package_service)]


def raise_exam_error(error: Exception) -> NoReturn:
    if isinstance(error, ExamNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, ExamVersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EXAM_VERSION_CONFLICT",
                "message": "Draft ujian telah berubah. Muat ulang sebelum melanjutkan.",
                "field_errors": {"expected_version": ["Versi draft tidak lagi berlaku."]},
                "details": {"current_version": error.current_version},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "PREREQUISITE_NOT_MET", "message": str(error)},
    ) from error


@router.get(
    "/lecturer/exam-queue",
    response_model=SuccessEnvelope[list[ExamQueueItemResponse]],
)
async def list_exam_queue(
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
) -> SuccessEnvelope[list[ExamQueueItemResponse]]:
    require_query_allowlist(request, set())
    return success(request, await service.list_queue(actor))


@router.get(
    "/lecturer/questions",
    response_model=SuccessEnvelope[list[QuestionVersionResponse]],
)
async def list_exam_questions(
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
) -> SuccessEnvelope[list[QuestionVersionResponse]]:
    require_query_allowlist(request, set())
    return success(request, await service.list_questions(actor))


@router.post(
    "/lecturer/questions",
    response_model=SuccessEnvelope[QuestionVersionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_exam_question(
    payload: QuestionVersionCreate,
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[QuestionVersionResponse]:
    try:
        claim = await idempotency.claim(
            actor_id=actor.user_id,
            idempotency_key=idempotency_key,
            method=request.method,
            normalized_path=request.url.path,
            payload=payload.model_dump(mode="json"),
            request_id=request_id(request),
        )
        if claim.replay_body is not None:
            return success(request, QuestionVersionResponse.model_validate(claim.replay_body))
        result = await service.create_question(actor, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (ExamNotFoundError, ExamConflictError) as error:
        raise_exam_error(error)


@router.post(
    "/exams",
    response_model=SuccessEnvelope[ExamResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_exam(
    payload: ExamCreate,
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[ExamResponse]:
    try:
        claim = await idempotency.claim(
            actor_id=actor.user_id,
            idempotency_key=idempotency_key,
            method=request.method,
            normalized_path=request.url.path,
            payload=payload.model_dump(mode="json"),
            request_id=request_id(request),
        )
        if claim.replay_body is not None:
            return success(request, ExamResponse.model_validate(claim.replay_body))
        result = await service.create_exam(actor, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (ExamNotFoundError, ExamConflictError) as error:
        raise_exam_error(error)


@router.get("/exams/{exam_id}", response_model=SuccessEnvelope[ExamResponse])
async def read_exam(
    exam_id: UUID,
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
) -> SuccessEnvelope[ExamResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.get_exam(actor, exam_id)
    except ExamNotFoundError as error:
        raise_exam_error(error)
    return success(request, result, version=result.row_version)


@router.patch("/exams/{exam_id}", response_model=SuccessEnvelope[ExamResponse])
async def update_exam(
    exam_id: UUID,
    payload: ExamUpdate,
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[ExamResponse]:
    try:
        claim = await idempotency.claim(
            actor_id=actor.user_id,
            idempotency_key=idempotency_key,
            method=request.method,
            normalized_path=request.url.path,
            payload=payload.model_dump(mode="json"),
            request_id=request_id(request),
        )
        if claim.replay_body is not None:
            return success(request, ExamResponse.model_validate(claim.replay_body))
        result = await service.update_exam(actor, exam_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (ExamNotFoundError, ExamConflictError) as error:
        raise_exam_error(error)


@router.put("/exams/{exam_id}/items", response_model=SuccessEnvelope[ExamResponse])
async def replace_exam_items(
    exam_id: UUID,
    payload: ExamItemsReplace,
    request: Request,
    actor: LecturerActorDependency,
    service: ExamPackageServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[ExamResponse]:
    try:
        claim = await idempotency.claim(
            actor_id=actor.user_id,
            idempotency_key=idempotency_key,
            method=request.method,
            normalized_path=request.url.path,
            payload=payload.model_dump(mode="json"),
            request_id=request_id(request),
        )
        if claim.replay_body is not None:
            return success(request, ExamResponse.model_validate(claim.replay_body))
        result = await service.replace_items(actor, exam_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (ExamNotFoundError, ExamConflictError) as error:
        raise_exam_error(error)
