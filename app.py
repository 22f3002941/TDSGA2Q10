from fastapi import FastAPI, Request, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import uuid
import time
import math

EMAIL = "22f3002941@ds.study.iitm.ac.in"

RATE_LIMIT = 10
WINDOW = 10

app = FastAPI()

# --------------------------------------------------------
# CORS
# --------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-qrh8ew.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# --------------------------------------------------------
# Request Context Middleware
# --------------------------------------------------------

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# --------------------------------------------------------
# Rate Limiter (Dependency)
# --------------------------------------------------------

buckets = defaultdict(deque)

def rate_limit(
    x_client_id: str | None = Header(None, alias="X-Client-Id"),
):

    client = x_client_id or "anonymous"

    now = time.time()

    bucket = buckets[client]

    while bucket and now - bucket[0] >= WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:

        retry_after = max(
            1,
            math.ceil(WINDOW - (now - bucket[0]))
        )

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry_after)
            },
        )

    bucket.append(now)


# --------------------------------------------------------
# Endpoint
# --------------------------------------------------------

@app.get("/ping")
def ping(
    request: Request,
    _: None = Depends(rate_limit),
):

    request_id = request.state.request_id

    response = JSONResponse(
        content={
            "email": EMAIL,
            "request_id": request_id,
        }
    )

    response.headers["X-Request-ID"] = request_id

    return response


# --------------------------------------------------------
# Root
# --------------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok"}


@app.head("/")
def head():
    return JSONResponse(content=None, status_code=200)


# --------------------------------------------------------
# Health
# --------------------------------------------------------

@app.get("/healthz")
def health():
    return {"status": "ok"}


# --------------------------------------------------------
# Debug
# --------------------------------------------------------

@app.get("/debug")
def debug():
    return {
        "clients": list(buckets.keys()),
        "bucket_count": len(buckets),
    }