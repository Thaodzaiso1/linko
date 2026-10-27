"""Pydantic v2 request and response contracts shared by every REST endpoint."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

ConnectionType = Literal["COLLEAGUE", "FRIEND", "MENTOR", "MENTEE", "TEAMMATE", "FOLLOW"]
ProjectMemberRole = Literal[
    "SPONSOR", "LEAD", "TECH_LEAD", "MEMBER", "CONTRIBUTOR", "ADVISOR", "PRODUCT", "TECH"
]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShortestPathRequest(ApiModel):
    source_id: int = Field(gt=0)
    target_id: int = Field(gt=0)
    max_hops: int = Field(default=6, ge=1, le=6)
    include_projects: bool = False


class ConnectionCreate(ApiModel):
    from_emp: int = Field(gt=0, validation_alias=AliasChoices("from_emp", "from_id"))
    to_emp: int = Field(gt=0, validation_alias=AliasChoices("to_emp", "to_id"))
    connection_type: ConnectionType = "COLLEAGUE"
    strength: Decimal = Field(default=Decimal("1.0"), ge=0, le=5, decimal_places=2)
    notes: str | None = Field(default=None, max_length=200)


class ConnectionUpdate(ApiModel):
    from_emp: int = Field(gt=0)
    to_emp: int = Field(gt=0)
    connection_type: ConnectionType | None = None
    strength: Decimal | None = Field(default=None, ge=0, le=5, decimal_places=2)
    notes: str | None = Field(default=None, max_length=200)


class ConnectionDelete(ApiModel):
    from_emp: int = Field(gt=0)
    to_emp: int = Field(gt=0)


class ProjectMemberCreate(ApiModel):
    employee_id: int = Field(gt=0)
    role: ProjectMemberRole = "MEMBER"


class CytoscapeNode(ApiModel):
    data: dict[str, Any]


class CytoscapeEdge(ApiModel):
    data: dict[str, Any]


class CytoscapeElements(ApiModel):
    nodes: list[CytoscapeNode] = Field(default_factory=list)
    edges: list[CytoscapeEdge] = Field(default_factory=list)


class PathStep(ApiModel):
    step: int
    from_id: int
    from_name: str
    to_id: int
    to_name: str
    from_type: Literal["Employee", "Project"] = "Employee"
    to_type: Literal["Employee", "Project"] = "Employee"
    relation_category: Literal["Knows", "ReportsTo", "WorksOn"]
    relation_detail: str
    direction: str
    strength: float | None = None


class ShortestPathResponse(ApiModel):
    found: bool
    source_id: int
    target_id: int
    max_hops: int
    include_projects: bool
    path_length: int | None
    message: str
    steps: list[PathStep] = Field(default_factory=list)
    elements: CytoscapeElements = Field(default_factory=CytoscapeElements)
    alternative_paths: list[dict[str, Any]] = Field(default_factory=list)


class EmployeeSummary(ApiModel):
    employee_id: int
    full_name: str
    email: str | None = None
    title: str | None = None
    status: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    manager_id: int | None = None
    manager_name: str | None = None


class NetworkCounts(ApiModel):
    outgoing: int = 0
    incoming: int = 0
    projects: int = 0


class EmployeeProfileResponse(ApiModel):
    employee: dict[str, Any]
    network_stats: NetworkCounts
    projects: list[dict[str, Any]]
    manager: dict[str, Any] | None
    direct_reports: list[dict[str, Any]]
    teammates: list[dict[str, Any]]
    social_connections: list[dict[str, Any]]


class GraphResponse(ApiModel):
    elements: CytoscapeElements
    data: list[dict[str, Any]] = Field(default_factory=list)
    message: str | None = None


class ComparisonResponse(ApiModel):
    manager_id: int
    graph_table: list[dict[str, Any]]
    connect_by: list[dict[str, Any]]
    comparison: dict[str, Any]
    elements: CytoscapeElements


class MutationResponse(ApiModel):
    success: bool = True
    ok: bool = True
    message: str
    record: dict[str, Any] | None = None
    audit_log: dict[str, Any] | None = None


class StatsResponse(ApiModel):
    vertices: dict[str, int]
    edges: dict[str, int]
    audit_logs: int
    connection_types: list[dict[str, Any]]


class HealthResponse(ApiModel):
    status: str
    database: str
    thin_mode: bool


class DepartmentResponse(ApiModel):
    department_id: int
    department_name: str
    location: str | None = None
    employee_count: int
    active_count: int


class ProjectResponse(ApiModel):
    project_id: int
    project_name: str
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str
    department_id: int | None = None
    department_name: str | None = None
    member_count: int


class TeammateCheckResponse(ApiModel):
    emp1: int
    emp2: int
    is_teammate: bool
    result: Literal["YES", "NO"]


class AuditLogResponse(ApiModel):
    log_id: int
    table_name: str | None = None
    action: str | None = None
    record_id: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    changed_by: str | None = None
    changed_at: str | None = None


class ProjectMemberResponse(ApiModel):
    message: str
    project_id: int
    employee_id: int
    role: str
    knows_before: int
    knows_after: int
    net_new_connections: int
    new_teammate_edges: list[dict[str, Any]] = Field(default_factory=list)
    new_teammate_edge_count: int
    warning: str | None = None


class DemoPresetResponse(ApiModel):
    name: str
    endpoint: str
    body: dict[str, Any] | None = None
