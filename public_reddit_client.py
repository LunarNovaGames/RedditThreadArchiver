"""
Public Reddit Client - Fetches data without authentication using public .json endpoints.
"""

import requests
import time
from typing import Optional
from models import Submission, Comment


class PublicRedditClient:
    """Reddit client using public .json endpoints (no authentication required)."""
    
    BASE_URL = "https://www.reddit.com"
    
    def __init__(self, user_agent: str = "RedditThreadArchiver/1.0.0"):
        """Initialize the public client."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent
        })
        self.min_request_interval = 2.0  # Be respectful with public API
        self.last_request_time = 0.0
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, url: str) -> dict:
        """Make a rate-limited request."""
        self._rate_limit()
        
        response = self.session.get(url)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited, waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return self._request(url)
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text[:200]}")
        
        return response.json()
    
    def get_submission(self, submission_id: str, subreddit: Optional[str] = None) -> Submission:
        """Get a submission by ID."""
        url = f"{self.BASE_URL}/comments/{submission_id}.json?limit=0"
        response = self._request(url)
        
        submission_data = response[0]["data"]["children"][0]["data"]
        
        return Submission(
            id=submission_data["id"],
            title=submission_data["title"],
            author=submission_data.get("author", "[deleted]"),
            selftext=submission_data.get("selftext", ""),
            created_utc=submission_data["created_utc"],
            subreddit=submission_data["subreddit"],
            url=submission_data["url"],
            permalink=submission_data["permalink"],
            num_comments=submission_data.get("num_comments", 0),
            comments=[]
        )
    
    def get_all_comments(self, submission_id: str, progress_callback=None) -> list[Comment]:
        """
        Get all comments for a submission using public API.
        
        Note: Public API has limitations on expanding "more" nodes,
        so we fetch with high limit and may not get all deeply nested comments.
        """
        url = f"{self.BASE_URL}/comments/{submission_id}.json?limit=500&depth=100&sort=old"
        response = self._request(url)
        
        comments: list[Comment] = []
        more_ids: list[str] = []
        fetched_ids: set[str] = set()
        
        if len(response) > 1:
            self._process_comment_listing(
                response[1]["data"]["children"],
                comments,
                more_ids,
                fetched_ids
            )
        
        if progress_callback:
            progress_callback(len(comments), len(more_ids))
        
        # Try to expand "more" nodes (public API has limitations here)
        max_expansions = 20  # Limit to avoid excessive requests
        expansions_done = 0
        
        while more_ids and expansions_done < max_expansions:
            batch = more_ids[:100]
            more_ids = more_ids[100:]
            
            try:
                # Use morechildren endpoint (works without auth for some cases)
                more_url = f"{self.BASE_URL}/api/morechildren.json"
                self._rate_limit()
                
                response = self.session.get(more_url, params={
                    "api_type": "json",
                    "link_id": f"t3_{submission_id}",
                    "children": ",".join(batch)
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if "json" in data and "data" in data["json"]:
                        things = data["json"]["data"].get("things", [])
                        self._process_comment_listing(things, comments, more_ids, fetched_ids)
                        expansions_done += 1
                        
                        if progress_callback:
                            progress_callback(len(comments), len(more_ids))
                else:
                    # Public API morechildren often fails, just skip
                    break
                    
            except Exception:
                # Skip expansion errors for public API
                break
        
        return comments
    
    def _process_comment_listing(
        self,
        children: list,
        comments: list[Comment],
        more_ids: list[str],
        fetched_ids: set[str]
    ):
        """Process a listing of comments/more nodes."""
        for thing in children:
            kind = thing.get("kind")
            data = thing.get("data", {})
            
            if kind == "t1":  # Comment
                comment_id = data.get("id")
                if comment_id and comment_id not in fetched_ids:
                    fetched_ids.add(comment_id)
                    
                    comment = Comment(
                        id=comment_id,
                        author=data.get("author", "[deleted]"),
                        body=data.get("body", ""),
                        created_utc=data.get("created_utc", 0),
                        parent_id=data.get("parent_id", ""),
                        permalink=data.get("permalink", ""),
                        score=data.get("score", 0),
                        is_submitter=data.get("is_submitter", False)
                    )
                    comments.append(comment)
                    
                    # Process nested replies
                    replies = data.get("replies")
                    if replies and isinstance(replies, dict):
                        reply_children = replies.get("data", {}).get("children", [])
                        self._process_comment_listing(
                            reply_children, comments, more_ids, fetched_ids
                        )
            
            elif kind == "more":  # More comments node
                children_ids = data.get("children", [])
                for child_id in children_ids:
                    if child_id and child_id not in fetched_ids:
                        more_ids.append(child_id)
