"""Pocketwatch.ai FastAPI Application — Multi-Tenant"""

from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import init_db
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# ── Import all public-schema models to register on PublicBase ──
from app.models.company import Company  # noqa: F401
from app.models.admin import Admin  # noqa: F401
from app.models.admin_otp import AdminOTP  # noqa: F401
from app.models.admin_refresh_token import AdminRefreshToken  # noqa: F401
from app.models.payment import PaymentMethod, Transaction, Subscription  # noqa: F401
from app.models.plan import CompanySubscription  # noqa: F401

# ── Routers ──
from app.routes.auth import router as admin_auth_router
from app.routes.users_auth import router as user_auth_router
from app.routes.admin_users import router as admin_users_router
from app.routes.payment import router as payment_router
from app.routes.plans import router as plans_router
from app.routes.setup_wizard import router as setup_wizard_router
from app.routes.dashboard import router as dashboard_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create public-schema tables. Tenant tables are provisioned on signup."""
    print(f"Starting {settings.APP_NAME} API...")
    init_db()
    print("Public schema tables ready.")
    yield
    print(f"Shutting down {settings.APP_NAME} API...")


app = FastAPI(
    title="Pocketwatch.ai API",
    description=(
        "Multi-tenant SPC & AI coaching platform for manufacturing.\n\n"
        "**Architecture**: Schema-per-tenant in PostgreSQL — each company gets its own "
        "`company_{id}` schema provisioned on signup."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Validation error handler (422) ────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return clean, readable validation errors instead of raw Pydantic output."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
        message = error["msg"].replace("Value error, ", "")
        errors.append(f"{field}: {message}" if field else message)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors[0] if len(errors) == 1 else errors},
    )


# ── Global exception handlers ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if settings.ENVIRONMENT == "development":
        import traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "traceback": traceback.format_exc()},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred"},
    )


# ── Routers ───────────────────────────────────────────────────
app.include_router(admin_auth_router)
app.include_router(user_auth_router)
app.include_router(admin_users_router)
app.include_router(payment_router)
app.include_router(plans_router)
app.include_router(setup_wizard_router)
app.include_router(dashboard_router)


# ── Health check ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "2.0.0",
        "architecture": "multi-tenant / schema-per-company",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
