"""
Reddit API Client - OAuth2 authenticated client for Reddit API.
"""

import requests
import time
from typing import Optional
from models import Submission, Comment
from config import Config


class RedditClient:
    """Reddit API client with OAuth2 authentication."""
    
    BASE_URL = "https://oauth.reddit.com"
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"
    
    def __init__(self, config: Config):
        """
        Initialize the Reddit client.
        
        Args:
            config: Configuration object with credentials
        """
        self.config = config
        self.access_token: Optional[str] = None
        self.token_expires: float = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.user_agent
        })
        
        # Rate limiting
        self.min_request_interval = 1.0  # seconds between requests
        self.last_request_time = 0.0
    
    def authenticate(self) -> bool:
        """
        Authenticate with Reddit using OAuth2 password grant.
        
        Returns:
            True if authentication successful
        """
        auth = (self.config.client_id, self.config.client_secret)
        data = {
            "grant_type": "password",
            "username": self.config.username,
            "password": self.config.password
        }
        headers = {
            "User-Agent": self.config.user_agent
        }
        
        response = requests.post(
            self.AUTH_URL,
            auth=auth,
            data=data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
        
        token_data = response.json()
        
        if "error" in token_data:
            raise Exception(f"Authentication error: {token_data['error']}")
        
        self.access_token = token_data["access_token"]
        self.token_expires = time.time() + token_data.get("expires_in", 3600)
        
        # Update session headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })
        
        return True
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Make an authenticated API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            **kwargs: Additional request parameters
            
        Returns:
            JSON response data
        """
        # Check token expiration
        if time.time() >= self.token_expires - 60:
            self.authenticate()
        
        self._rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited, waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return self._request(method, endpoint, **kwargs)
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_submission(self, submission_id: str, subreddit: Optional[str] = None) -> Submission:
        """
        Get a submission by ID.
        
        Args:
            submission_id: Reddit submission ID
            subreddit: Optional subreddit name
            
        Returns:
            Submission object
        """
        if subreddit:
            endpoint = f"/r/{subreddit}/comments/{submission_id}"
        else:
            endpoint = f"/comments/{submission_id}"
        
        response = self._request("GET", endpoint, params={"limit": 0})
        
        # Response is a list: [submission_listing, comments_listing]
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
    
    def get_all_comments(self, submission_id: str) -> list[Comment]:
        """
        Get all comments for a submission, including expanding "more" nodes.
        
        Args:
            submission_id: Reddit submission ID
            
        Returns:
            List of all Comment objects
        """
        # Initial fetch
        endpoint = f"/comments/{submission_id}"
        response = self._request("GET", endpoint, params={"limit": 500, "depth": 100})
        
        comments: list[Comment] = []
        more_ids: list[str] = []
        fetched_ids: set[str] = set()
        
        # Process comments listing
        if len(response) > 1:
            self._process_comment_listing(
                response[1]["data"]["children"],
                comments,
                more_ids,
                fetched_ids
            )
        
        # Expand all "more" nodes
        while more_ids:
            batch = more_ids[:100]
            more_ids = more_ids[100:]
            
            print(f"  Expanding {len(batch)} more comments ({len(more_ids)} remaining)...")
            
            try:
                more_response = self._request(
                    "GET",
                    "/api/morechildren",
                    params={
                        "api_type": "json",
                        "link_id": f"t3_{submission_id}",
                        "children": ",".join(batch)
                    }
                )
                
                if "json" in more_response and "data" in more_response["json"]:
                    things = more_response["json"]["data"].get("things", [])
                    self._process_comment_listing(things, comments, more_ids, fetched_ids)
                    
            except Exception as e:
                print(f"  Warning: Failed to expand more comments: {e}")
        
        return comments
    
    def _process_comment_listing(
        self,
        children: list,
        comments: list[Comment],
        more_ids: list[str],
        fetched_ids: set[str]
    ):
        """
        Process a listing of comments/more nodes.
        
        Args:
            children: List of thing objects from Reddit API
            comments: Output list for comments
            more_ids: Output list for "more" IDs to expand
            fetched_ids: Set of already fetched comment IDs
        """
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
