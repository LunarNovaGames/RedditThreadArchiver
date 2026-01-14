# RedditThreadArchiver

A Python tool for extracting and archiving Reddit threads with full comment trees. Designed for researchers, archivists, and data analysts who need complete, accurate snapshots of Reddit discussions.

## Features

- **Complete Comment Retrieval**: Fetches all comments including deeply nested replies
- **OAuth2 Authentication**: Uses Reddit's official API with proper authentication
- **"More Comments" Expansion**: Automatically expands collapsed comment threads
- **Verbatim Extraction**: Preserves exact text without modification
- **Flexible Filtering**: Filter responses by specific authors or criteria
- **Multiple Output Formats**: JSON, Markdown, and plain text output
- **GUI Application**: Web-based interface with real-time progress tracking

## GUI Application (Recommended)

The easiest way to use this tool is through the web GUI:

```bash
# Terminal 1: Start the backend
pip install -r requirements.txt
python server.py

# Terminal 2: Start the frontend
cd gui
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

### GUI Features
- Paste any Reddit thread URL or submission ID
- Specify which accounts to capture (one per line)
- Real-time progress with live comment counts
- Export to JSON or plain text
- Copy to clipboard or save to file

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/RedditThreadArchiver.git
cd RedditThreadArchiver

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Create a Reddit application at https://www.reddit.com/prefs/apps
2. Select "script" as the application type
3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=RedditThreadArchiver/1.0.0
```

## Usage

### Basic Usage

```bash
# Extract a thread by submission ID
python archiver.py --submission 1q870w5

# Extract with author filtering
python archiver.py --submission 1q870w5 --authors "Larian_Swen,Larian_David"

# Output to specific format
python archiver.py --submission 1q870w5 --format markdown --output results.md
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--submission` | Reddit submission ID (required) |
| `--subreddit` | Subreddit name (optional, for context) |
| `--authors` | Comma-separated list of authors to filter responses |
| `--format` | Output format: `json`, `markdown`, `text` (default: `markdown`) |
| `--output` | Output file path (default: stdout) |
| `--include-deleted` | Include [deleted] comments (default: false) |

### Job Runner (Recommended for Multiple Extractions)

Create a `jobs.json` configuration file:

```json
{
    "jobs": [
        {
            "name": "Larian AMA",
            "description": "Extract Q&A from Larian Studios AMA",
            "submission_id": "1q870w5",
            "subreddit": "Games",
            "filter": {
                "answer_authors": ["LarSwen", "Larian_Swen", "larianstudios"],
                "include_deleted": false
            },
            "output": {
                "format": "markdown",
                "file": "output/larian_ama.md"
            }
        }
    ]
}
```

Run jobs:

```bash
# List available jobs
python job_runner.py --list

# Run all jobs
python job_runner.py --config jobs.json

# Run a specific job
python job_runner.py --config jobs.json --job "Larian AMA"

# Dry run (validate without executing)
python job_runner.py --config jobs.json --dry-run
```

### Python API

```python
from archiver import RedditArchiver

# Initialize with credentials
archiver = RedditArchiver(
    client_id="your_client_id",
    client_secret="your_client_secret",
    username="your_username",
    password="your_password"
)

# Fetch a submission with all comments
thread = archiver.fetch_submission("1q870w5")

# Filter for specific authors
qa_pairs = archiver.extract_qa_pairs(
    thread,
    answer_authors=["Larian_Swen", "Larian_David"]
)

# Export results
archiver.export_markdown(qa_pairs, "output.md")
```

## Project Structure

```
RedditThreadArchiver/
├── archiver.py          # Main extraction script
├── reddit_client.py     # Reddit API client wrapper
├── models.py            # Data models
├── exporters.py         # Output format handlers
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## API Rate Limiting

This tool respects Reddit's API rate limits:
- Maximum 60 requests per minute
- Automatic backoff on 429 responses
- Configurable delays between requests

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is intended for legitimate archival and research purposes. Users are responsible for complying with Reddit's [API Terms of Use](https://www.reddit.com/wiki/api-terms) and [Content Policy](https://www.redditinc.com/policies/content-policy).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
