from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import uuid
import time

EMAIL = "22f3002941@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-qrh8ew.example.com",
    "https://exam.sanand.workers.dev",
]

RATE_LIMIT = 10
WINDOW = 10

app = FastAPI()

# ----------------------------------------------------
# CORS
# ----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ----------------------------------------------------
# Rate Limiter
# ----------------------------------------------------

buckets = defaultdict(deque)

@app.middleware("http")
async def rate_limit(request: Request, call_next):

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()
    bucket = buckets[client_id]

    while bucket and now - bucket[0] >= WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    bucket.append(now)

    return await call_next(request)

# ----------------------------------------------------
# Request Context
# ----------------------------------------------------

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    # Also set here for completeness
    response.headers["X-Request-ID"] = request_id

    return response

# ----------------------------------------------------
# Endpoint
# ----------------------------------------------------

@app.get("/ping")
async def ping(request: Request):

    request_id = request.state.request_id

    response = JSONResponse(
        content={
            "email": EMAIL,
            "request_id": request_id,
        }
    )

    # Explicitly set the response header
    response.headers["X-Request-ID"] = request_id

    return response

# ----------------------------------------------------
# Root
# ----------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok"}

@app.head("/")
def root_head():
    return JSONResponse(status_code=200, content=None)

# ----------------------------------------------------
# Health
# ----------------------------------------------------

@app.get("/healthz")
def health():
    return {"status": "ok"}

# ----------------------------------------------------
# Debug
# ----------------------------------------------------

@app.get("/debug")
def debug():

    return {
        "clients": list(buckets.keys()),
        "bucket_count": len(buckets),
    }