from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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
)

# ----------------------------------------------------
# Rate limiter
# ----------------------------------------------------

buckets = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):

    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    bucket = buckets[client]

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

    response.headers["X-Request-ID"] = request_id

    return response


# ----------------------------------------------------
# Endpoint
# ----------------------------------------------------

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


# ----------------------------------------------------
# Root
# ----------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok"}


@app.head("/")
def root_head():
    return JSONResponse(status_code=200, content=None)