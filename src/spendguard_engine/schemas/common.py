from __future__ import annotations

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    name: str | None = None


class AgentCreateResponse(BaseModel):
    agent_id: str


class BudgetSetRequest(BaseModel):
    hard_limit_cents: int = Field(gt=0)
    topup_cents: int = Field(ge=0, default=0)


class BudgetResponse(BaseModel):
    agent_id: str
    hard_limit_cents: int
    remaining_cents: int
    locked_cents: int
    locked_run_id: str | None = None
    locked_expires_at: str | None = None
