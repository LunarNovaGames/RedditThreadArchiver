"""
Job Runner - Execute extraction jobs from configuration file.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Optional

from archiver import RedditArchiver


def load_jobs(config_path: str) -> dict:
    """Load job configuration from JSON file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_job(job: dict, archiver: RedditArchiver, dry_run: bool = False) -> bool:
    """
    Execute a single extraction job.
    
    Args:
        job: Job configuration dictionary
        archiver: Initialized RedditArchiver instance
        dry_run: If True, only validate without executing
        
    Returns:
        True if job completed successfully
    """
    name = job.get("name", "Unnamed Job")
    description = job.get("description", "")
    submission_id = job.get("submission_id")
    subreddit = job.get("subreddit")
    
    print(f"\n{'=' * 60}")
    print(f"Job: {name}")
    if description:
        print(f"Description: {description}")
    print(f"Submission: {submission_id}")
    print(f"{'=' * 60}")
    
    if not submission_id:
        print("ERROR: Missing submission_id", file=sys.stderr)
        return False
    
    if dry_run:
        print("[DRY RUN] Would execute this job")
        return True
    
    try:
        # Fetch submission
        submission = archiver.fetch_submission(submission_id, subreddit)
        print(f"Title: {submission.title}")
        print(f"Comments retrieved: {len(submission.comments)}")
        
        # Get filter settings
        filter_config = job.get("filter", {})
        answer_authors = filter_config.get("answer_authors", [])
        include_deleted = filter_config.get("include_deleted", False)
        
        if not answer_authors:
            print("WARNING: No answer_authors specified, dumping raw data")
            # Just output submission info
            output_config = job.get("output", {})
            output_format = output_config.get("format", "json")
            output_file = output_config.get("file")
            
            if output_file:
                Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {submission.title}\n\n")
                    f.write(f"Author: {submission.author}\n")
                    f.write(f"Comments: {len(submission.comments)}\n\n")
                    f.write(submission.selftext)
                print(f"Output written to: {output_file}")
            return True
        
        # Extract Q&A pairs
        print(f"Filtering for authors: {answer_authors}")
        qa_pairs = archiver.extract_qa_pairs(
            submission,
            answer_authors=answer_authors,
            include_deleted=include_deleted
        )
        
        print(f"Q&A pairs found: {len(qa_pairs)}")
        
        # Export results
        output_config = job.get("output", {})
        output_format = output_config.get("format", "markdown")
        output_file = output_config.get("file")
        
        if output_file:
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        if output_format == "markdown":
            content = archiver.export_markdown(qa_pairs, output_file)
        elif output_format == "json":
            content = archiver.export_json(qa_pairs, output_file)
        else:
            content = archiver.export_text(qa_pairs, output_file)
        
        if output_file:
            print(f"Output written to: {output_file}")
        else:
            print(content)
        
        return True
        
    except Exception as e:
        print(f"ERROR: Job failed - {e}", file=sys.stderr)
        return False


def main():
    """Command-line entry point for job runner."""
    parser = argparse.ArgumentParser(
        description="Run extraction jobs from configuration file."
    )
    parser.add_argument(
        "--config", "-c",
        default="jobs.json",
        help="Path to jobs configuration file (default: jobs.json)"
    )
    parser.add_argument(
        "--job", "-j",
        help="Run only the job with this name (default: run all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without executing"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_jobs",
        help="List available jobs and exit"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_jobs(args.config)
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {args.config}", file=sys.stderr)
        print("Create a jobs.json file or copy jobs.example.json", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config: {e}", file=sys.stderr)
        sys.exit(1)
    
    jobs = config.get("jobs", [])
    
    if args.list_jobs:
        print("Available jobs:")
        for job in jobs:
            print(f"  - {job.get('name', 'Unnamed')}: {job.get('description', 'No description')}")
        sys.exit(0)
    
    # Initialize archiver
    archiver = RedditArchiver()
    
    # Authenticate
    if not args.dry_run:
        if not archiver.authenticate():
            print("ERROR: Failed to authenticate with Reddit API", file=sys.stderr)
            sys.exit(1)
    
    # Run jobs
    if args.job:
        # Run specific job
        job = next((j for j in jobs if j.get("name") == args.job), None)
        if not job:
            print(f"ERROR: Job not found: {args.job}", file=sys.stderr)
            sys.exit(1)
        success = run_job(job, archiver, args.dry_run)
        sys.exit(0 if success else 1)
    else:
        # Run all jobs
        results = []
        for job in jobs:
            success = run_job(job, archiver, args.dry_run)
            results.append((job.get("name", "Unnamed"), success))
        
        print(f"\n{'=' * 60}")
        print("Summary:")
        for name, success in results:
            status = "✓" if success else "✗"
            print(f"  {status} {name}")
        
        failed = sum(1 for _, s in results if not s)
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
