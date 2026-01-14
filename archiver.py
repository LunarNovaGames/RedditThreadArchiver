"""
RedditThreadArchiver - Reddit Thread Extraction Tool

A complete tool for extracting Reddit threads with full comment trees,
designed for archival, research, and data analysis purposes.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from typing import Optional

from config import Config
from reddit_client import RedditClient
from models import Submission, Comment, QAPair
from exporters import MarkdownExporter, JSONExporter, TextExporter


class RedditArchiver:
    """Main archiver class for extracting Reddit threads."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Initialize the archiver with Reddit API credentials.
        
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            username: Reddit username
            password: Reddit password
            user_agent: Custom user agent string
        """
        self.config = Config(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        self.client = RedditClient(self.config)
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Reddit API using OAuth2.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self._authenticated = self.client.authenticate()
            return self._authenticated
        except Exception as e:
            print(f"Authentication failed: {e}", file=sys.stderr)
            return False
    
    def fetch_submission(self, submission_id: str, subreddit: Optional[str] = None) -> Submission:
        """
        Fetch a submission with all comments.
        
        Args:
            submission_id: Reddit submission ID
            subreddit: Optional subreddit name (for faster lookup)
            
        Returns:
            Submission object with full comment tree
        """
        if not self._authenticated:
            if not self.authenticate():
                raise RuntimeError("Failed to authenticate with Reddit API")
        
        print(f"Fetching submission {submission_id}...")
        submission = self.client.get_submission(submission_id, subreddit)
        
        print(f"Fetching comments (this may take a while)...")
        comments = self.client.get_all_comments(submission_id)
        submission.comments = comments
        
        print(f"Retrieved {len(comments)} comments")
        return submission
    
    def extract_qa_pairs(
        self,
        submission: Submission,
        answer_authors: list[str],
        include_deleted: bool = False
    ) -> list[QAPair]:
        """
        Extract Q&A pairs where answers are from specified authors.
        
        Args:
            submission: Submission with comments
            answer_authors: List of usernames whose replies count as answers
            include_deleted: Whether to include deleted comments
            
        Returns:
            List of QAPair objects
        """
        # Normalize author names for comparison
        answer_authors_lower = [a.lower() for a in answer_authors]
        
        # Build comment lookup by ID
        comment_map: dict[str, Comment] = {}
        for comment in submission.comments:
            comment_map[comment.id] = comment
        
        qa_pairs: list[QAPair] = []
        
        # Find all comments by answer authors
        for comment in submission.comments:
            if comment.author and comment.author.lower() in answer_authors_lower:
                # Skip deleted/removed unless requested
                if not include_deleted:
                    if comment.body in ("[deleted]", "[removed]"):
                        continue
                
                # Find the parent question
                parent_id = comment.parent_id
                if parent_id.startswith("t1_"):
                    # Parent is a comment
                    parent_comment_id = parent_id[3:]
                    if parent_comment_id in comment_map:
                        parent = comment_map[parent_comment_id]
                        
                        # Skip deleted parents unless requested
                        if not include_deleted:
                            if parent.body in ("[deleted]", "[removed]"):
                                continue
                        
                        # Check if we already have a QA pair for this question
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
                
                elif parent_id.startswith("t3_"):
                    # Parent is the submission itself (top-level answer)
                    # This shouldn't typically be a Q&A pair
                    pass
        
        # Sort by question timestamp (chronological order)
        qa_pairs.sort(key=lambda qa: qa.question.created_utc)
        
        # Sort answers within each pair by timestamp
        for qa in qa_pairs:
            qa.answers.sort(key=lambda a: a.created_utc)
        
        return qa_pairs
    
    def export_markdown(self, qa_pairs: list[QAPair], output_path: Optional[str] = None) -> str:
        """Export Q&A pairs to Markdown format."""
        exporter = MarkdownExporter()
        content = exporter.export(qa_pairs)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return content
    
    def export_json(self, qa_pairs: list[QAPair], output_path: Optional[str] = None) -> str:
        """Export Q&A pairs to JSON format."""
        exporter = JSONExporter()
        content = exporter.export(qa_pairs)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return content
    
    def export_text(self, qa_pairs: list[QAPair], output_path: Optional[str] = None) -> str:
        """Export Q&A pairs to plain text format."""
        exporter = TextExporter()
        content = exporter.export(qa_pairs)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return content


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Extract and archive Reddit threads with full comment trees."
    )
    parser.add_argument(
        "--submission", "-s",
        required=True,
        help="Reddit submission ID to extract"
    )
    parser.add_argument(
        "--subreddit", "-r",
        help="Subreddit name (optional, for faster lookup)"
    )
    parser.add_argument(
        "--authors", "-a",
        help="Comma-separated list of authors to filter for answers"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "json", "text"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--include-deleted",
        action="store_true",
        help="Include [deleted] and [removed] comments"
    )
    
    args = parser.parse_args()
    
    # Initialize archiver
    archiver = RedditArchiver()
    
    # Fetch submission
    try:
        submission = archiver.fetch_submission(args.submission, args.subreddit)
    except Exception as e:
        print(f"Error fetching submission: {e}", file=sys.stderr)
        sys.exit(1)
    
    # If authors specified, extract Q&A pairs
    if args.authors:
        authors = [a.strip() for a in args.authors.split(",")]
        qa_pairs = archiver.extract_qa_pairs(
            submission,
            answer_authors=authors,
            include_deleted=args.include_deleted
        )
        
        # Export based on format
        if args.format == "markdown":
            content = archiver.export_markdown(qa_pairs, args.output)
        elif args.format == "json":
            content = archiver.export_json(qa_pairs, args.output)
        else:
            content = archiver.export_text(qa_pairs, args.output)
        
        if not args.output:
            print(content)
        else:
            print(f"Exported {len(qa_pairs)} Q&A pairs to {args.output}")
    
    else:
        # Just export raw submission data
        print(f"Submission: {submission.title}")
        print(f"Author: {submission.author}")
        print(f"Comments: {len(submission.comments)}")
        print("\nUse --authors to filter for specific responders")


if __name__ == "__main__":
    main()
