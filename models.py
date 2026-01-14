"""
Data Models - Dataclasses for Reddit objects.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Comment:
    """Represents a Reddit comment."""
    id: str
    author: str
    body: str
    created_utc: float
    parent_id: str
    permalink: str
    score: int = 0
    is_submitter: bool = False
    
    def __repr__(self) -> str:
        preview = self.body[:50] + "..." if len(self.body) > 50 else self.body
        return f"Comment(id={self.id}, author={self.author}, body='{preview}')"


@dataclass
class Submission:
    """Represents a Reddit submission."""
    id: str
    title: str
    author: str
    selftext: str
    created_utc: float
    subreddit: str
    url: str
    permalink: str
    num_comments: int = 0
    comments: list[Comment] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"Submission(id={self.id}, title='{self.title}', comments={len(self.comments)})"


@dataclass
class QAPair:
    """Represents a question and its answer(s)."""
    question: Comment
    answers: list[Comment] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"QAPair(question_id={self.question.id}, answers={len(self.answers)})"
