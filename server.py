"""
FastAPI Backend Server for Reddit Thread Archiver GUI.

Provides REST API endpoints for extraction and real-time progress via SSE.
"""

import asyncio
import json
import uuid
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import Config
from reddit_client import RedditClient
from models import Submission, Comment, QAPair


# In-memory job storage
jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    yield
    # Cleanup jobs on shutdown
    jobs.clear()


app = FastAPI(
    title="Reddit Thread Archiver API",
    description="Backend API for extracting Q&A from Reddit threads",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractionRequest(BaseModel):
    """Request body for starting extraction."""
    submission_id: str
    accounts: list[str]


class ExtractionResponse(BaseModel):
    """Response with job ID."""
    job_id: str


@app.post("/api/extract", response_model=ExtractionResponse)
async def start_extraction(request: ExtractionRequest):
    """Start a new extraction job."""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "pending",
        "submission_id": request.submission_id,
        "accounts": request.accounts,
        "progress": {
            "phase": "Initializing...",
            "comments_fetched": 0,
            "expansions_remaining": 0,
            "matches_found": 0,
            "percent": 0
        },
        "result": None,
        "error": None
    }
    
    # Start extraction in background
    asyncio.create_task(run_extraction(job_id))
    
    return ExtractionResponse(job_id=job_id)


async def run_extraction(job_id: str):
    """Run the extraction process for a job."""
    job = jobs.get(job_id)
    if not job:
        return
    
    try:
        job["status"] = "running"
        
        # Initialize client
        job["progress"]["phase"] = "Authenticating..."
        job["progress"]["percent"] = 5
        
        config = Config()
        client = RedditClient(config)
        
        # Authenticate (run in thread pool since it's blocking)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, client.authenticate)
        
        job["progress"]["phase"] = "Fetching submission..."
        job["progress"]["percent"] = 10
        
        # Fetch submission
        submission = await loop.run_in_executor(
            None,
            lambda: client.get_submission(job["submission_id"])
        )
        
        job["progress"]["phase"] = "Fetching comments..."
        job["progress"]["percent"] = 20
        
        # Fetch all comments with progress updates
        comments = await fetch_comments_with_progress(client, job["submission_id"], job)
        submission.comments = comments
        
        job["progress"]["phase"] = "Filtering Q&A pairs..."
        job["progress"]["percent"] = 90
        
        # Extract Q&A pairs
        qa_pairs = extract_qa_pairs(submission, job["accounts"])
        
        job["progress"]["matches_found"] = len(qa_pairs)
        job["progress"]["phase"] = "Complete"
        job["progress"]["percent"] = 100
        
        # Store result
        job["result"] = {
            "submission_id": submission.id,
            "submission_title": submission.title,
            "total_comments": len(comments),
            "qa_pairs": [
                {
                    "question": {
                        "id": qa.question.id,
                        "author": qa.question.author,
                        "body": qa.question.body,
                        "created_utc": qa.question.created_utc,
                        "permalink": qa.question.permalink
                    },
                    "answers": [
                        {
                            "id": a.id,
                            "author": a.author,
                            "body": a.body,
                            "created_utc": a.created_utc,
                            "permalink": a.permalink
                        }
                        for a in qa.answers
                    ]
                }
                for qa in qa_pairs
            ]
        }
        
        job["status"] = "complete"
        
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


async def fetch_comments_with_progress(
    client: RedditClient,
    submission_id: str,
    job: dict
) -> list[Comment]:
    """Fetch comments with progress updates."""
    loop = asyncio.get_event_loop()
    
    # This is a simplified version - in production, you'd want to 
    # hook into the client's progress callbacks
    comments = await loop.run_in_executor(
        None,
        lambda: client.get_all_comments(submission_id)
    )
    
    job["progress"]["comments_fetched"] = len(comments)
    
    return comments


def extract_qa_pairs(submission: Submission, accounts: list[str]) -> list[QAPair]:
    """Extract Q&A pairs where answers are from specified accounts."""
    accounts_lower = [a.lower() for a in accounts]
    
    # Build comment lookup
    comment_map: dict[str, Comment] = {}
    for comment in submission.comments:
        comment_map[comment.id] = comment
    
    qa_pairs: list[QAPair] = []
    
    # Find answers from target accounts
    for comment in submission.comments:
        if comment.author and comment.author.lower() in accounts_lower:
            if comment.body in ("[deleted]", "[removed]"):
                continue
            
            parent_id = comment.parent_id
            if parent_id.startswith("t1_"):
                parent_comment_id = parent_id[3:]
                if parent_comment_id in comment_map:
                    parent = comment_map[parent_comment_id]
                    
                    if parent.body in ("[deleted]", "[removed]"):
                        continue
                    
                    existing = next(
                        (qa for qa in qa_pairs if qa.question.id == parent.id),
                        None
                    )
                    
                    if existing:
                        existing.answers.append(comment)
                    else:
                        qa_pairs.append(QAPair(
                            question=parent,
                            answers=[comment]
                        ))
    
    # Sort by question timestamp
    qa_pairs.sort(key=lambda qa: qa.question.created_utc)
    
    # Sort answers within each pair
    for qa in qa_pairs:
        qa.answers.sort(key=lambda a: a.created_utc)
    
    return qa_pairs


@app.get("/api/progress/{job_id}")
async def stream_progress(job_id: str):
    """Stream progress updates via Server-Sent Events."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator():
        last_progress = None
        
        while True:
            job = jobs.get(job_id)
            if not job:
                break
            
            current_progress = json.dumps(job["progress"])
            
            # Send progress update if changed
            if current_progress != last_progress:
                yield f"data: {json.dumps({'type': 'progress', **job['progress']})}\n\n"
                last_progress = current_progress
            
            # Check for completion
            if job["status"] == "complete":
                yield f"data: {json.dumps({'type': 'complete', **job['result']})}\n\n"
                break
            
            # Check for error
            if job["status"] == "error":
                yield f"data: {json.dumps({'type': 'error', 'message': job['error']})}\n\n"
                break
            
            await asyncio.sleep(0.2)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
