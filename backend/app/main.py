from __future__ import annotations

import json
from pathlib import Path

import base64
import os
import secrets
from datetime import timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.schemas import (
    AIProviderConnectionTest,
    AIProviderSettings,
    AIProviderSettingsUpdate,
    ApprovalPolicy,
    ApprovalPolicyUpdate,
    AccountLogin,
    AnalyticsDashboard,
    BackgroundJob,
    BackgroundJobLog,
    CalendarEvent,
    CalendarEventCreate,
    CompanyProfile,
    CompanyProfileUpdate,
    ContentArtifact,
    ContentBrief,
    ContentOpportunity,
    CurrentWorkspace,
    DeletionReceipt,
    Draft,
    DraftCreateResult,
    DraftPublishCreate,
    DraftScheduleCreate,
    DraftStatus,
    DraftUpdate,
    JobKind,
    KnowledgeReadiness,
    LinkedInIntegration,
    LinkedInIntegrationUpdate,
    ModelCallLog,
    OnboardingDecision,
    OnboardingState,
    OnboardingStep,
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    PerformanceMetricsCreate,
    PostMemory,
    PreferenceSuggestion,
    PreferenceSuggestionDecision,
    PublishingConnection,
    PublishingOAuthStart,
    PublishingOAuthCallback,
    PublishingProvider,
    PublishResult,
    ReviewDecisionCreate,
    ReviewerPackage,
    RetrievalQuery,
    RetrievalResult,
    SignupCreate,
    Source,
    SourceCreate,
    SourceDetail,
    SourceUpdate,
    StrategyDashboard,
    TrendSignal,
    TrendSignalCreate,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
    now_utc,
)
from app.risk_checks import high_risk_unsupported_claims
from app.store import (
    ApprovalBlockedError,
    AuthenticationError,
    DataStore,
    NotFoundError,
    PermissionDeniedError,
    ReviewDecisionRequiredError,
)
from app.providers import resolve_secret_reference


ROOT = Path(__file__).resolve().parents[2]


def env_value(name: str, legacy_name: str | None = None, default: str | None = None) -> str | None:
    return resolve_secret_reference(name) or (resolve_secret_reference(legacy_name) if legacy_name else None) or default


def build_store() -> DataStore:
    data_backend = env_value("VOUCH_DATA_BACKEND", "QUAINY_DATA_BACKEND", "memory").strip().lower()
    if data_backend == "postgres":
        from app.postgres_store import PostgresDataStore

        database_url = resolve_secret_reference("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when VOUCH_DATA_BACKEND=postgres.")
        return PostgresDataStore(database_url, ROOT / "docs" / "architecture" / "database_schema.sql")
    return DataStore()


store = build_store()


def enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def fixture_mode() -> str:
    environment = env_value("VOUCH_ENV", "QUAINY_ENV", "development").strip().lower()
    data_backend = env_value("VOUCH_DATA_BACKEND", "QUAINY_DATA_BACKEND", "memory").strip().lower()
    explicit_mode = env_value("VOUCH_FIXTURE_MODE", "QUAINY_FIXTURE_MODE")
    explicit_seed = env_value("VOUCH_ENABLE_DEV_SEED", "QUAINY_ENABLE_DEV_SEED")

    if environment == "production":
        if enabled(explicit_seed) or (explicit_mode and explicit_mode.strip().lower() != "none"):
            raise RuntimeError("Deterministic fixtures cannot be enabled when VOUCH_ENV=production.")
        return "none"
    if explicit_mode:
        return explicit_mode.strip().lower()
    if explicit_seed is not None:
        return "sample" if enabled(explicit_seed) else "none"
    return "sample" if data_backend == "memory" else "none"


FIXTURE_MODE = fixture_mode()
SEEDED_ORG_ID = store.seed_quainy(ROOT) if FIXTURE_MODE == "sample" else None

app = FastAPI(title="Quainy Vouch API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def not_found(error: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error))


def approval_blocked(error: ApprovalBlockedError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(error))


def bad_review_decision(error: ReviewDecisionRequiredError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


def permission_denied(error: PermissionDeniedError) -> HTTPException:
    return HTTPException(status_code=403, detail=str(error))


def authentication_failed(error: AuthenticationError) -> HTTPException:
    return HTTPException(status_code=401, detail=str(error))


def generation_failed(error: RuntimeError) -> HTTPException:
    message = str(error)
    provider_failure_markers = (
        "provider request failed",
        "runtime availability",
        "request timed out",
        "quota",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
    )
    status_code = 502 if any(marker.lower() in message.lower() for marker in provider_failure_markers) else 422
    return HTTPException(status_code=status_code, detail=message)


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise AuthenticationError("Authorization header must use Bearer token.")
    return authorization[len(prefix) :].strip()


def allow_fixture_fallback() -> bool:
    return FIXTURE_MODE == "sample"


def actor_from_auth(
    organization_id: str,
    authorization: str | None,
    fallback_actor_id: str | None = None,
) -> str:
    token = bearer_token(authorization)
    if token:
        return store.actor_id_for_token(token, organization_id)
    if allow_fixture_fallback():
        return fallback_actor_id or "local_user"
    raise AuthenticationError("Authentication required.")


def actor_from_optional_auth(organization_id: str, authorization: str | None) -> str | None:
    token = bearer_token(authorization)
    if token:
        return store.actor_id_for_token(token, organization_id)
    if allow_fixture_fallback():
        return None
    raise AuthenticationError("Authentication required.")


def require_org_role(
    organization_id: str,
    authorization: str | None,
    allowed_roles: set[UserRole],
    fallback_actor_id: str | None = None,
) -> str:
    actor_id = actor_from_auth(organization_id, authorization, fallback_actor_id)
    store.require_role(organization_id, actor_id, allowed_roles)
    return actor_id


def build_publishing_oauth_start(organization_id: str, provider: str, frontend_origin: str | None = None) -> PublishingOAuthStart:
    provider_key, config = publishing_oauth_config(provider)
    client_id = first_env(config["client_id_env"])
    redirect_uri = first_env(config["redirect_uri_env"])
    if not client_id or not redirect_uri:
        raise HTTPException(status_code=400, detail=f"{provider_key.title()} OAuth is not configured.")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope_value_from_config(config["scope_env"], str(config["default_scope"])),
        "state": publishing_oauth_state(organization_id, provider_key, frontend_origin),
    }
    return PublishingOAuthStart(
        provider=provider_key,
        authorization_url=f"{config['authorize_url']}?{urlencode(params)}",
    )


def publishing_oauth_config(provider: str) -> tuple[str, dict[str, object]]:
    provider_key = provider.strip().lower()
    configs: dict[str, dict[str, object]] = {
        "linkedin": {
            "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
            "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
            "client_id_env": ("LINKEDIN_CLIENT_ID", "QUAINY_LINKEDIN_CLIENT_ID"),
            "client_secret_env": ("LINKEDIN_CLIENT_SECRET", "QUAINY_LINKEDIN_CLIENT_SECRET"),
            "redirect_uri_env": ("LINKEDIN_REDIRECT_URI", "QUAINY_LINKEDIN_REDIRECT_URI"),
            "scope_env": ("LINKEDIN_SCOPES", "QUAINY_LINKEDIN_SCOPES"),
            "default_scope": "openid profile w_member_social r_organization_social w_organization_social",
            "default_target_type": "company_page",
        },
        "reddit": {
            "authorize_url": "https://www.reddit.com/api/v1/authorize",
            "token_url": "https://www.reddit.com/api/v1/access_token",
            "client_id_env": ("REDDIT_CLIENT_ID", "QUAINY_REDDIT_CLIENT_ID"),
            "client_secret_env": ("REDDIT_CLIENT_SECRET", "QUAINY_REDDIT_CLIENT_SECRET"),
            "redirect_uri_env": ("REDDIT_REDIRECT_URI", "QUAINY_REDDIT_REDIRECT_URI"),
            "scope_env": ("REDDIT_SCOPES", "QUAINY_REDDIT_SCOPES"),
            "default_scope": "identity read submit",
            "default_target_type": "community",
        },
        "instagram": {
            "authorize_url": f"https://www.facebook.com/{meta_oauth_version()}/dialog/oauth",
            "token_url": f"https://graph.facebook.com/{meta_oauth_version()}/oauth/access_token",
            "client_id_env": ("INSTAGRAM_CLIENT_ID", "QUAINY_INSTAGRAM_CLIENT_ID"),
            "client_secret_env": ("INSTAGRAM_CLIENT_SECRET", "QUAINY_INSTAGRAM_CLIENT_SECRET"),
            "redirect_uri_env": ("INSTAGRAM_REDIRECT_URI", "QUAINY_INSTAGRAM_REDIRECT_URI"),
            "scope_env": ("INSTAGRAM_SCOPES", "QUAINY_INSTAGRAM_SCOPES"),
            "default_scope": "pages_show_list instagram_basic instagram_content_publish",
            "default_target_type": "business_account",
        },
    }
    if provider_key not in configs:
        raise HTTPException(status_code=404, detail="Publishing provider not supported.")
    return provider_key, configs[provider_key]


def complete_publishing_oauth_callback(provider: str, code: str, state: str, actor_id: str = "local_user") -> tuple[PublishingOAuthCallback, str | None]:
    state_parts = state.split(":")
    if len(state_parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")
    organization_id, state_provider = state_parts[0], state_parts[1]
    frontend_origin = decode_frontend_origin_state(state_parts[3]) if len(state_parts) >= 4 else None
    provider_key, config = publishing_oauth_config(provider)
    if state_provider != provider_key:
        raise HTTPException(status_code=400, detail="OAuth provider state mismatch.")
    store.get_organization(organization_id)
    token_payload = exchange_publishing_oauth_code(provider_key, config, code)
    account_metadata = fetch_publishing_account_metadata(provider_key, str(token_payload.get("access_token") or ""))
    selected_target = first_publishing_target(provider_key, account_metadata)
    scopes = scopes_from_token_payload(token_payload, config["scope_env"], str(config["default_scope"]))
    expires_at = None
    if token_payload.get("expires_in") is not None:
        try:
            expires_at = now_utc() + timedelta(seconds=int(token_payload["expires_in"]))
        except (TypeError, ValueError):
            expires_at = None
    connection = store.get_publishing_connection(organization_id, PublishingProvider(provider_key))
    connection = connection.model_copy(
        update={
            "oauth_status": "validated",
            "scopes": scopes,
            "access_token": str(token_payload.get("access_token") or ""),
            "refresh_token": str(token_payload.get("refresh_token") or connection.refresh_token or "") or None,
            "token_type": str(token_payload.get("token_type") or "bearer"),
            "expires_at": expires_at,
            "account_id": account_id_from_metadata(account_metadata) or account_id_from_token_payload(provider_key, token_payload),
            "account_name": account_name_from_metadata(account_metadata) or account_name_from_token_payload(provider_key, token_payload),
            "selected_target_type": str(config["default_target_type"]),
            "selected_target_id": selected_target.get("id") or default_target_id(provider_key, token_payload),
            "selected_target_name": selected_target.get("name") or default_target_name(provider_key, token_payload),
            "publishing_enabled": True,
        }
    )
    saved = store.upsert_publishing_connection(connection, actor_id)
    callback = PublishingOAuthCallback(
        provider=PublishingProvider(provider_key),
        status="connected",
        message=f"{provider_key.title()} connected.",
        connection=saved,
    )
    return callback, frontend_origin


def exchange_publishing_oauth_code(provider: str, config: dict[str, object], code: str) -> dict[str, object]:
    client_id = first_env(config["client_id_env"])  # type: ignore[arg-type]
    client_secret = first_env(config["client_secret_env"])  # type: ignore[arg-type]
    redirect_uri = first_env(config["redirect_uri_env"])  # type: ignore[arg-type]
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=400, detail=f"{provider.title()} OAuth token exchange is not configured.")
    body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    request = Request(
        str(config["token_url"]),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"{provider.title()} OAuth token exchange failed.") from error


def fetch_publishing_account_metadata(provider: str, access_token: str) -> dict[str, object]:
    if not access_token:
        return {}
    try:
        if provider == "linkedin":
            account = oauth_get_json("https://api.linkedin.com/v2/userinfo", access_token)
            pages = oauth_get_json(
                "https://api.linkedin.com/v2/organizationAcls"
                "?q=roleAssignee&role=ADMINISTRATOR&projection=(elements*(organization,organization~(localizedName)))",
                access_token,
            )
            return {"account": account, "targets": linkedin_company_targets(pages)}
        if provider == "reddit":
            account = oauth_get_json("https://oauth.reddit.com/api/v1/me", access_token)
            return {"account": account}
        if provider == "instagram":
            account = oauth_get_json(
                f"https://graph.facebook.com/{meta_oauth_version()}/me?fields=id,name",
                access_token,
            )
            pages = oauth_get_json(
                f"https://graph.facebook.com/{meta_oauth_version()}/me/accounts"
                "?fields=id,name,instagram_business_account{id,username}",
                access_token,
            )
            return {"account": account, "targets": instagram_business_targets(pages)}
    except Exception:
        return {}
    return {}


def oauth_get_json(url: str, access_token: str) -> dict[str, object]:
    request = Request(url, headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def linkedin_company_targets(payload: dict[str, object]) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    elements = payload.get("elements")
    if not isinstance(elements, list):
        return targets
    for item in elements:
        if not isinstance(item, dict):
            continue
        organization = item.get("organization")
        organization_detail = item.get("organization~")
        target_id = str(organization or "")
        target_name = ""
        if isinstance(organization_detail, dict):
            target_name = str(organization_detail.get("localizedName") or "")
        if target_id:
            targets.append({"id": target_id, "name": target_name})
    return targets


def instagram_business_targets(payload: dict[str, object]) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    pages = payload.get("data")
    if not isinstance(pages, list):
        return targets
    for page in pages:
        if not isinstance(page, dict):
            continue
        account = page.get("instagram_business_account")
        if not isinstance(account, dict):
            continue
        target_id = str(account.get("id") or "")
        target_name = str(account.get("username") or page.get("name") or "")
        if target_id:
            targets.append({"id": target_id, "name": target_name})
    return targets


def first_publishing_target(provider: str, metadata: dict[str, object]) -> dict[str, str]:
    targets = metadata.get("targets")
    if isinstance(targets, list) and targets and isinstance(targets[0], dict):
        return {key: str(value) for key, value in targets[0].items() if value is not None}
    return {}


def scopes_from_token_payload(payload: dict[str, object], scope_env: object, default_scope: str) -> list[str]:
    scope_value = payload.get("scope") or scope_value_from_config(scope_env, default_scope)
    if isinstance(scope_value, str):
        return [scope for scope in scope_value.replace(",", " ").split() if scope]
    return []


def scope_value_from_config(scope_env: object, default_scope: str) -> str:
    if isinstance(scope_env, tuple):
        return first_env(scope_env) or default_scope
    return os.getenv(str(scope_env)) or default_scope


def account_id_from_token_payload(provider: str, payload: dict[str, object]) -> str | None:
    for key in ("account_id", "user_id", "id", "sub"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def account_id_from_metadata(metadata: dict[str, object]) -> str | None:
    account = metadata.get("account")
    if isinstance(account, dict):
        for key in ("sub", "id", "name"):
            value = account.get(key)
            if value:
                return str(value)
    return None


def account_name_from_token_payload(provider: str, payload: dict[str, object]) -> str | None:
    for key in ("account_name", "name", "username"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def account_name_from_metadata(metadata: dict[str, object]) -> str | None:
    account = metadata.get("account")
    if isinstance(account, dict):
        for key in ("name", "localizedFirstName", "preferred_username"):
            value = account.get(key)
            if value:
                return str(value)
    return None


def default_target_id(provider: str, payload: dict[str, object]) -> str | None:
    if provider == "linkedin":
        return str(payload.get("page_urn") or payload.get("organization_urn") or "") or None
    if provider == "reddit":
        return str(payload.get("subreddit") or "") or None
    if provider == "instagram":
        return str(payload.get("instagram_business_account_id") or payload.get("page_id") or "") or None
    return None


def default_target_name(provider: str, payload: dict[str, object]) -> str | None:
    if provider == "linkedin":
        return str(payload.get("page_name") or payload.get("organization_name") or "") or None
    if provider == "reddit":
        return str(payload.get("subreddit_name") or payload.get("subreddit") or "") or None
    if provider == "instagram":
        return str(payload.get("instagram_business_account_name") or payload.get("page_name") or "") or None
    return None


def first_env(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = resolve_secret_reference(name)
        if value:
            return value
    return None


def meta_oauth_version() -> str:
    return resolve_secret_reference("META_OAUTH_VERSION") or resolve_secret_reference("QUAINY_META_OAUTH_VERSION") or "v20.0"


def frontend_url() -> str:
    return (
        resolve_secret_reference("VOUCH_FRONTEND_URL")
        or resolve_secret_reference("QUAINY_FRONTEND_URL")
        or "http://127.0.0.1:5173"
    ).rstrip("/")


def publishing_oauth_state(organization_id: str, provider_key: str, frontend_origin: str | None = None) -> str:
    state_parts = [organization_id, provider_key, secrets.token_urlsafe(24)]
    trusted_origin = trusted_frontend_origin(frontend_origin)
    if trusted_origin:
        state_parts.append(base64.urlsafe_b64encode(trusted_origin.encode("utf-8")).decode("ascii").rstrip("="))
    return ":".join(state_parts)


def trusted_frontend_origin(origin: str | None) -> str | None:
    if not origin:
        return None
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        return None
    normalized = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    configured = {frontend_url()}
    local_hosts = {"localhost", "127.0.0.1"}
    if normalized in configured or parsed.hostname in local_hosts:
        return normalized
    return None


def decode_frontend_origin_state(value: str) -> str | None:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    return trusted_frontend_origin(decoded)


def publishing_oauth_redirect(callback: PublishingOAuthCallback, frontend_origin: str | None = None) -> RedirectResponse:
    query = urlencode(
        {
            "oauth_provider": callback.provider.value,
            "oauth_status": callback.status,
            "oauth_message": callback.message,
        }
    )
    return RedirectResponse(f"{trusted_frontend_origin(frontend_origin) or frontend_url()}/?{query}", status_code=303)


def summarize_list_result(items: list[object], id_attr: str = "id") -> dict[str, object]:
    return {
        "count": len(items),
        "ids": [getattr(item, id_attr) for item in items if getattr(item, id_attr, None)],
    }


def summarize_one_result(item: object, id_attr: str = "id") -> dict[str, object]:
    item_id = getattr(item, id_attr, None)
    return {"id": item_id} if item_id else {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "seeded_organization_id": SEEDED_ORG_ID or ""}


@app.get("/bootstrap")
def bootstrap() -> dict[str, object]:
    if not SEEDED_ORG_ID:
        raise HTTPException(status_code=404, detail="Development bootstrap workspace is disabled.")
    org = store.get_organization(SEEDED_ORG_ID)
    return {
        "organization": org,
        "profile": store.profiles[org.id],
        "sources": store.list_sources(org.id),
        "opportunities": store.list_opportunities(org.id),
        "memory": store.list_memory(org.id),
    }


@app.post("/auth/signup")
def signup(payload: SignupCreate) -> dict[str, object]:
    try:
        token, workspace = store.signup(payload)
        return {"token": token, "workspace": workspace}
    except PermissionDeniedError as error:
        raise permission_denied(error) from error


@app.post("/auth/login")
def login(payload: AccountLogin) -> dict[str, object]:
    try:
        token, workspace = store.login(payload)
        return {"token": token, "workspace": workspace}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/me", response_model=CurrentWorkspace)
def current_workspace(authorization: str | None = Header(default=None)) -> CurrentWorkspace:
    try:
        token = bearer_token(authorization)
        if not token:
            raise AuthenticationError("Authentication required.")
        return store.current_workspace(token)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/onboarding/profile", response_model=OnboardingState)
def decide_onboarding_profile(
    organization_id: str,
    payload: OnboardingDecision,
    authorization: str | None = Header(default=None),
) -> OnboardingState:
    try:
        actor_id = actor_from_auth(organization_id, authorization, None)
        return store.decide_onboarding_profile(organization_id, actor_id, payload)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations", response_model=Organization)
def create_organization(payload: OrganizationCreate) -> Organization:
    return store.create_organization(payload)


@app.get("/organizations", response_model=list[Organization])
def list_organizations(authorization: str | None = Header(default=None)) -> list[Organization]:
    try:
        token = bearer_token(authorization)
        if token:
            return [store.current_workspace(token).organization]
        if allow_fixture_fallback():
            return store.list_organizations()
        raise AuthenticationError("Authentication required.")
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}", response_model=Organization)
def get_organization(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> Organization:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_organization(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}", response_model=Organization)
def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Organization:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_organization(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/deactivate", response_model=Organization)
def deactivate_organization(
    organization_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Organization:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.deactivate_organization(organization_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/activate", response_model=Organization)
def activate_organization(
    organization_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Organization:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.activate_organization(organization_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/users", response_model=list[User])
def list_users(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[User]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_users(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/users", response_model=User)
def create_user(
    organization_id: str,
    payload: UserCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> User:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.create_user(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/users/{user_id}", response_model=User)
def update_user(
    organization_id: str,
    user_id: str,
    payload: UserUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> User:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_user(organization_id, user_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/approval-policy", response_model=ApprovalPolicy)
def get_approval_policy(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> ApprovalPolicy:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_approval_policy(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/approval-policy", response_model=ApprovalPolicy)
def update_approval_policy(
    organization_id: str,
    payload: ApprovalPolicyUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> ApprovalPolicy:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_approval_policy(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/ai-provider-settings", response_model=AIProviderSettings)
def get_ai_provider_settings(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> AIProviderSettings:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_ai_provider_settings(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/ai-provider-settings", response_model=AIProviderSettings)
def update_ai_provider_settings(
    organization_id: str,
    payload: AIProviderSettingsUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> AIProviderSettings:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_ai_provider_settings(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/ai-provider-settings/test", response_model=AIProviderConnectionTest)
def test_ai_provider_settings(
    organization_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> AIProviderConnectionTest:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.test_ai_provider_settings(organization_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.delete("/organizations/{organization_id}", response_model=DeletionReceipt)
def delete_organization(
    organization_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> DeletionReceipt:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.delete_organization(organization_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/profile", response_model=CompanyProfile)
def get_profile(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> CompanyProfile:
    try:
        actor_from_optional_auth(organization_id, authorization)
        store.get_organization(organization_id)
        return store.profiles[organization_id]
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/profile", response_model=CompanyProfile)
def update_profile(
    organization_id: str,
    payload: CompanyProfileUpdate,
    authorization: str | None = Header(default=None),
) -> CompanyProfile:
    try:
        actor = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        profile = store.update_profile(organization_id, payload, actor)
        if bearer_token(authorization):
            store.mark_onboarding_step(organization_id, actor, OnboardingStep.profile_started, profile_skipped=False)
        return profile
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/linkedin-integration", response_model=LinkedInIntegration)
def get_linkedin_integration(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> LinkedInIntegration:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.get_linkedin_integration(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/organizations/{organization_id}/linkedin-integration", response_model=LinkedInIntegration)
def update_linkedin_integration(
    organization_id: str,
    payload: LinkedInIntegrationUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> LinkedInIntegration:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return store.update_linkedin_integration(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/publishing-connections", response_model=list[PublishingConnection])
def list_publishing_connections(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PublishingConnection]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_publishing_connections(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/publishing-connections/{provider}/oauth/start", response_model=PublishingOAuthStart)
def start_publishing_oauth(
    organization_id: str,
    provider: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
    origin: str | None = Header(default=None),
) -> PublishingOAuthStart:
    try:
        require_org_role(organization_id, authorization, {UserRole.owner}, actor_id)
        return build_publishing_oauth_start(organization_id, provider, origin)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/publishing-connections/{provider}/oauth/callback")
def finish_publishing_oauth(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
):
    callback, frontend_origin = complete_publishing_oauth_callback(provider, code, state)
    return publishing_oauth_redirect(callback, frontend_origin)


@app.post("/organizations/{organization_id}/sources", response_model=Source)
def create_source(
    organization_id: str,
    payload: SourceCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Source:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        source = store.create_source(organization_id, payload, actor_id)
        store.run_job(
            organization_id,
            actor_id,
            JobKind.source_ingest,
            "source",
            source.id,
            {"source_id": source.id, "source_type": source.source_type},
            lambda: store.ingest_source(source.id, actor_id),
            lambda chunks: {"chunk_count": len(chunks)},
        )
        if authorization:
            store.mark_onboarding_step(organization_id, actor_id, OnboardingStep.source_added)
        return source
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/sources", response_model=list[Source])
def list_sources(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[Source]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_sources(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/knowledge-readiness", response_model=KnowledgeReadiness)
def knowledge_readiness(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> KnowledgeReadiness:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.knowledge_readiness(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/sources/{source_id}", response_model=SourceDetail)
def get_source(
    source_id: str,
    authorization: str | None = Header(default=None),
) -> SourceDetail:
    try:
        source = store.get_source(source_id)
        actor_from_optional_auth(source.organization_id, authorization)
        return store.get_source_detail(source_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/sources/{source_id}", response_model=Source)
def update_source(
    source_id: str,
    payload: SourceUpdate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> Source:
    try:
        source = store.get_source(source_id)
        actor_id = require_org_role(source.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.update_source(source_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/sources/{source_id}/ingest")
def ingest_source(
    source_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        source = store.get_source(source_id)
        actor_id = require_org_role(source.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        _job, chunks = store.run_job(
            source.organization_id,
            actor_id,
            JobKind.source_ingest,
            "source",
            source_id,
            {"source_id": source_id},
            lambda: store.ingest_source(source_id, actor_id),
            lambda result: {"chunk_count": len(result)},
        )
        return {"source_id": source_id, "chunk_count": len(chunks), "chunks": chunks}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/sources/{source_id}/refresh")
def refresh_source(
    source_id: str,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        source = store.get_source(source_id)
        actor_id = require_org_role(source.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        _job, chunks = store.run_job(
            source.organization_id,
            actor_id,
            JobKind.source_refresh,
            "source",
            source_id,
            {"source_id": source_id},
            lambda: store.ingest_source(source_id, actor_id),
            lambda result: {"chunk_count": len(result)},
        )
        return {"chunks": chunks, "message": "Source refreshed from the selected page snapshot."}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/retrieval/query", response_model=list[RetrievalResult])
def retrieve_source_chunks(
    organization_id: str,
    payload: RetrievalQuery,
    authorization: str | None = Header(default=None),
) -> list[RetrievalResult]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return [
            RetrievalResult(chunk=chunk, source=source, score=score)
            for chunk, source, score in store.retrieve_chunks(organization_id, payload.query, payload.limit)
        ]
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/opportunities/generate")
def generate_opportunities(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, opportunities = store.run_job(
            organization_id,
            actor_id,
            JobKind.opportunity_generation,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.generate_opportunities(organization_id, actor_id),
            summarize_list_result,
        )
        if actor_id:
            store.mark_onboarding_step(organization_id, actor_id, OnboardingStep.first_opportunity_generated)
        if not opportunities:
            return {"opportunities": [], "message": "No strong opportunity found from approved context."}
        return {"opportunities": opportunities}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except RuntimeError as error:
        raise generation_failed(error) from error


@app.get("/organizations/{organization_id}/opportunities")
def list_opportunities(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[object]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_opportunities(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/opportunities/{opportunity_id}/dismiss", response_model=ContentOpportunity)
def dismiss_opportunity(
    opportunity_id: str,
    payload: ReviewDecisionCreate,
    authorization: str | None = Header(default=None),
) -> ContentOpportunity:
    try:
        opportunity = store.get_opportunity(opportunity_id)
        actor_id = require_org_role(opportunity.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.dismiss_opportunity(opportunity_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/calendar-events", response_model=list[CalendarEvent])
def list_calendar_events(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[CalendarEvent]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_calendar_events(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/calendar-events", response_model=CalendarEvent)
def create_calendar_event(
    organization_id: str,
    payload: CalendarEventCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> CalendarEvent:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.create_calendar_event(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/trend-signals", response_model=list[TrendSignal])
def list_trend_signals(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[TrendSignal]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_trend_signals(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/trend-signals", response_model=TrendSignal)
def create_trend_signal(
    organization_id: str,
    payload: TrendSignalCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> TrendSignal:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.create_trend_signal(organization_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/trend-opportunities/generate")
def generate_trend_opportunities(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, opportunities = store.run_job(
            organization_id,
            actor_id,
            JobKind.trend_opportunity_generation,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.generate_trend_opportunities(organization_id, actor_id),
            summarize_list_result,
        )
        return {"opportunities": opportunities}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/opportunities/{opportunity_id}/briefs", response_model=ContentBrief)
def create_brief(
    opportunity_id: str,
    authorization: str | None = Header(default=None),
) -> ContentBrief:
    try:
        opportunity = store.get_opportunity(opportunity_id)
        actor_id = require_org_role(opportunity.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        brief = store.create_brief(opportunity_id, actor_id)
        if actor_id:
            store.mark_onboarding_step(brief.organization_id, actor_id, OnboardingStep.first_brief_created)
        return brief
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except RuntimeError as error:
        raise generation_failed(error) from error


@app.get("/opportunities/{opportunity_id}", response_model=ContentOpportunity)
def get_opportunity(
    opportunity_id: str,
    authorization: str | None = Header(default=None),
) -> ContentOpportunity:
    try:
        opportunity = store.get_opportunity(opportunity_id)
        actor_from_optional_auth(opportunity.organization_id, authorization)
        return opportunity
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/briefs/{brief_id}", response_model=ContentBrief)
def get_brief(
    brief_id: str,
    authorization: str | None = Header(default=None),
) -> ContentBrief:
    try:
        brief = store.get_brief(brief_id)
        actor_from_optional_auth(brief.organization_id, authorization)
        return brief
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/briefs/{brief_id}/drafts", response_model=list[Draft])
def list_brief_drafts(
    brief_id: str,
    authorization: str | None = Header(default=None),
) -> list[Draft]:
    try:
        brief = store.get_brief(brief_id)
        actor_from_optional_auth(brief.organization_id, authorization)
        return store.list_drafts_for_brief(brief_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/briefs/{brief_id}/drafts", response_model=DraftCreateResult)
def generate_drafts(
    brief_id: str,
    platform: str = "linkedin",
    content_type: str = "company_post",
    reddit_community: str = "",
    reddit_rules: str = "",
    authorization: str | None = Header(default=None),
) -> DraftCreateResult:
    try:
        brief = store.get_brief(brief_id)
        actor_id = require_org_role(brief.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, drafts = store.run_job(
            brief.organization_id,
            actor_id,
            JobKind.draft_generation,
            "brief",
            brief_id,
            {
                "brief_id": brief_id,
                "platform": platform,
                "content_type": content_type,
                "reddit_community": reddit_community,
                "reddit_rules": reddit_rules,
            },
            lambda: store.generate_drafts(brief_id, platform, content_type, actor_id, reddit_community, reddit_rules),
            summarize_list_result,
        )
        if drafts:
            if actor_id:
                store.mark_onboarding_step(drafts[0].organization_id, actor_id, OnboardingStep.first_draft_created)
        return DraftCreateResult(drafts=drafts)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except RuntimeError as error:
        raise generation_failed(error) from error


@app.get("/drafts/{draft_id}", response_model=Draft)
def get_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> Draft:
    try:
        draft = store.get_draft(draft_id)
        actor_from_optional_auth(draft.organization_id, authorization)
        return draft
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.patch("/drafts/{draft_id}", response_model=Draft)
def update_draft(
    draft_id: str,
    payload: DraftUpdate,
    authorization: str | None = Header(default=None),
) -> Draft:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.update_draft_body(draft_id, payload.body, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/drafts/{draft_id}/reviewer-package", response_model=ReviewerPackage)
def reviewer_package(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> ReviewerPackage:
    try:
        draft = store.get_draft(draft_id)
        actor_from_optional_auth(draft.organization_id, authorization)
        brief = store.get_brief(draft.content_brief_id)
        opportunity = store.get_opportunity(brief.opportunity_id)
        sources = [store.get_source(source_id) for source_id in brief.source_ids]
        source_chunks = [chunk for chunk in store.approved_chunks(draft.organization_id) if chunk.source_id in brief.source_ids]
        unsupported = high_risk_unsupported_claims(draft.claims)
        approval_progress = store.approval_progress(draft.id)
        draft.approval_metadata = approval_progress
        if unsupported:
            suggested_action = "Review unsupported claims before approval."
        elif approval_progress["remaining_reviewer_count"]:
            suggested_action = f"Needs {approval_progress['remaining_reviewer_count']} more approval(s)."
        else:
            suggested_action = "Ready for human approval."
        return ReviewerPackage(
            draft=draft,
            brief=brief,
            opportunity=opportunity,
            sources=sources,
            source_chunks=source_chunks,
            decision_history=store.list_draft_decisions(draft.id),
            suggested_action=suggested_action,
        )
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/regenerate", response_model=DraftCreateResult)
def regenerate_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> DraftCreateResult:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, drafts = store.run_job(
            draft.organization_id,
            actor_id,
            JobKind.draft_regeneration,
            "draft",
            draft_id,
            {"draft_id": draft_id},
            lambda: store.regenerate_drafts_for_draft(draft_id, actor_id),
            summarize_list_result,
        )
        return DraftCreateResult(drafts=drafts)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    payload: ReviewDecisionCreate,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.reviewer}, actor_id)
        decision = store.approve_draft(draft_id, payload, actor_id)
        draft = store.get_draft(draft_id)
        if bearer_token(authorization) and draft.status == DraftStatus.approved:
            store.mark_onboarding_step(draft.organization_id, actor_id, OnboardingStep.first_artifact_approved)
        return decision
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/reject")
def reject_draft(
    draft_id: str,
    payload: ReviewDecisionCreate,
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.reviewer}, "local_user")
        return store.reject_draft(draft_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ReviewDecisionRequiredError as error:
        raise bad_review_decision(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/export")
def export_draft(
    draft_id: str,
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.export_draft(draft_id, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/schedule")
def schedule_draft(
    draft_id: str,
    payload: DraftScheduleCreate,
    authorization: str | None = Header(default=None),
) -> object:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        return store.schedule_draft(draft_id, payload.scheduled_for, payload.reason, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/drafts/{draft_id}/publish/linkedin", response_model=PublishResult)
def publish_draft_to_linkedin(
    draft_id: str,
    payload: DraftPublishCreate,
    authorization: str | None = Header(default=None),
) -> PublishResult:
    try:
        draft = store.get_draft(draft_id)
        actor_id = require_org_role(draft.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, result = store.run_job(
            draft.organization_id,
            actor_id,
            JobKind.linkedin_publish,
            "draft",
            draft_id,
            payload.model_dump(mode="json"),
            lambda: store.publish_draft_to_linkedin(draft_id, payload, actor_id),
            lambda publish_result: publish_result.model_dump(mode="json"),
        )
        return result
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except ApprovalBlockedError as error:
        raise approval_blocked(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/jobs", response_model=list[BackgroundJob])
def list_jobs(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[BackgroundJob]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_jobs(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/model-calls", response_model=list[ModelCallLog])
def list_model_calls(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[ModelCallLog]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_model_call_logs(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, BackgroundJob | list[BackgroundJobLog]]:
    try:
        job = store.get_job(job_id)
        actor_from_optional_auth(job.organization_id, authorization)
        return {"job": job, "logs": store.list_job_logs(job_id)}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, BackgroundJob | list[BackgroundJobLog]]:
    try:
        job = store.get_job(job_id)
        actor_id = require_org_role(job.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        job = store.reset_job_for_retry(job_id, actor_id)
        if job.kind in {JobKind.source_ingest, JobKind.source_refresh}:
            store.run_existing_job(
                job.id,
                lambda: store.ingest_source(job.entity_id, actor_id),
                lambda chunks: {"chunk_count": len(chunks)},
            )
        elif job.kind == JobKind.opportunity_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_opportunities(job.organization_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.trend_opportunity_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_trend_opportunities(job.organization_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.draft_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_drafts(
                    str(job.payload["brief_id"]),
                    str(job.payload.get("platform", "linkedin")),
                    str(job.payload.get("content_type", "company_post")),
                    actor_id,
                    str(job.payload.get("reddit_community", "")),
                    str(job.payload.get("reddit_rules", "")),
                ),
                summarize_list_result,
            )
        elif job.kind == JobKind.draft_regeneration:
            store.run_existing_job(
                job.id,
                lambda: store.regenerate_drafts_for_draft(job.entity_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.linkedin_publish:
            payload = DraftPublishCreate(**job.payload)
            store.run_existing_job(
                job.id,
                lambda: store.publish_draft_to_linkedin(job.entity_id, payload, actor_id),
                lambda result: result.model_dump(mode="json"),
            )
        elif job.kind == JobKind.analytics_import:
            store.run_existing_job(
                job.id,
                lambda: store.import_linkedin_analytics(job.organization_id, actor_id),
                summarize_list_result,
            )
        elif job.kind == JobKind.performance_capture:
            payload = PerformanceMetricsCreate(**job.payload)
            store.run_existing_job(
                job.id,
                lambda: store.record_performance_metrics(job.entity_id, payload, actor_id),
                summarize_one_result,
            )
        elif job.kind == JobKind.preference_suggestion_generation:
            store.run_existing_job(
                job.id,
                lambda: store.generate_preference_suggestions(job.organization_id, actor_id),
                summarize_list_result,
            )
        else:
            raise PermissionDeniedError("This job kind cannot be retried.")
        return {"job": store.get_job(job.id), "logs": store.list_job_logs(job.id)}
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
    except RuntimeError as error:
        raise generation_failed(error) from error


@app.get("/organizations/{organization_id}/memory")
def memory(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[object]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_memory(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/preference-suggestions", response_model=list[PreferenceSuggestion])
def list_preference_suggestions(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PreferenceSuggestion]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_preference_suggestions(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/preference-suggestions/generate", response_model=list[PreferenceSuggestion])
def generate_preference_suggestions(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PreferenceSuggestion]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, suggestions = store.run_job(
            organization_id,
            actor_id,
            JobKind.preference_suggestion_generation,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.generate_preference_suggestions(organization_id, actor_id),
            summarize_list_result,
        )
        return suggestions
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/preference-suggestions/{suggestion_id}/approve", response_model=PreferenceSuggestion)
def approve_preference_suggestion(
    suggestion_id: str,
    payload: PreferenceSuggestionDecision,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> PreferenceSuggestion:
    try:
        suggestion = store.get_preference_suggestion(suggestion_id)
        actor_id = require_org_role(suggestion.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.approve_preference_suggestion(suggestion_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/preference-suggestions/{suggestion_id}/dismiss", response_model=PreferenceSuggestion)
def dismiss_preference_suggestion(
    suggestion_id: str,
    payload: PreferenceSuggestionDecision,
    actor_id: str = "local_user",
    authorization: str | None = Header(default=None),
) -> PreferenceSuggestion:
    try:
        suggestion = store.get_preference_suggestion(suggestion_id)
        actor_id = require_org_role(suggestion.organization_id, authorization, {UserRole.owner, UserRole.editor}, actor_id)
        return store.dismiss_preference_suggestion(suggestion_id, payload, actor_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/memory/{memory_id}/performance", response_model=PostMemory)
def record_memory_performance(
    memory_id: str,
    payload: PerformanceMetricsCreate,
    authorization: str | None = Header(default=None),
) -> PostMemory:
    try:
        memory_item = store.get_memory(memory_id)
        actor_id = require_org_role(memory_item.organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, memory = store.run_job(
            memory_item.organization_id,
            actor_id,
            JobKind.performance_capture,
            "post_memory",
            memory_id,
            payload.model_dump(mode="json"),
            lambda: store.record_performance_metrics(memory_id, payload, actor_id),
            summarize_one_result,
        )
        return memory
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.post("/organizations/{organization_id}/analytics/import", response_model=list[PostMemory])
def import_linkedin_analytics(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[PostMemory]:
    try:
        actor_id = require_org_role(organization_id, authorization, {UserRole.owner, UserRole.editor}, "local_user")
        _job, imported = store.run_job(
            organization_id,
            actor_id,
            JobKind.analytics_import,
            "organization",
            organization_id,
            {"organization_id": organization_id},
            lambda: store.import_linkedin_analytics(organization_id, actor_id),
            summarize_list_result,
        )
        return imported
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except PermissionDeniedError as error:
        raise permission_denied(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/analytics", response_model=AnalyticsDashboard)
def analytics_dashboard(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> AnalyticsDashboard:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.analytics_dashboard(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/strategy", response_model=StrategyDashboard)
def strategy_dashboard(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> StrategyDashboard:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.strategy_dashboard(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/content-artifacts", response_model=list[ContentArtifact])
def content_artifacts(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[ContentArtifact]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_content_artifacts(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/calendar", response_model=list[Draft])
def calendar(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[Draft]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_calendar(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error


@app.get("/organizations/{organization_id}/audit-logs")
def audit_logs(
    organization_id: str,
    authorization: str | None = Header(default=None),
) -> list[object]:
    try:
        actor_from_optional_auth(organization_id, authorization)
        return store.list_audit_logs(organization_id)
    except AuthenticationError as error:
        raise authentication_failed(error) from error
    except NotFoundError as error:
        raise not_found(error) from error
