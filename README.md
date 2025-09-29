# Zoom Recordings Extractor

A comprehensive tool for downloading all cloud recordings from a Zoom account with organized storage, resume capability, and rate limiting.

## Features

- **Complete Extraction**: Downloads all file types (MP4, M4A, chat, transcript, captions, timeline JSON, etc.)
- **Organized Storage**: Clean, date- and user-based folder structure
- **Resumable**: Can resume interrupted extractions
- **Rate Limiting**: Respects Zoom's API limits with exponential backoff
- **Hands-off Operation**: Runs autonomously once started
- **Edge Case Handling**: Handles trash, passcodes, UUID encoding, and other gotchas
- **Comprehensive Logging**: Detailed logs and inventory tracking

## Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Setup

### 1. Create Zoom S2S OAuth App

1. Go to [Zoom Marketplace](https://marketplace.zoom.us/)
2. Sign in and click "Develop" → "Build App"
3. Choose "Server-to-Server OAuth" app type
4. Fill in app information
5. **Important**: Add these scopes:
   - `recording:read`
   - `user:read`
   - `meeting:read`
6. Get your **Account ID**, **Client ID**, and **Client Secret**

### 2. Configure Environment

Copy `env.example` to `.env` and fill in your credentials:

```bash
cp env.example .env
```

Edit `.env`:
```env
# Required: Zoom S2S OAuth Credentials
ZOOM_ACCOUNT_ID=your_account_id_here
ZOOM_CLIENT_ID=your_client_id_here
ZOOM_CLIENT_SECRET=your_client_secret_here

# Optional: Date range (defaults to last 30 days)
ZOOM_FROM=2024-01-01
ZOOM_TO=2024-12-31

# Optional: User filter (comma-separated emails or user IDs)
ZOOM_USER_FILTER=user1@company.com,user2@company.com

# Optional: Output directory (defaults to ./zoom_recordings)
ZOOM_OUTDIR=./zoom_recordings

# Optional: Download settings
MAX_CONCURRENT_DOWNLOADS=2
DOWNLOAD_TIMEOUT=300
CHUNK_SIZE=8388608
```

## Usage

### Basic Usage

```bash
python zoom_extract.py
```

### Advanced Usage

```bash
python zoom_extract.py \
  --output-dir ./my_recordings \
  --from-date 2024-01-01 \
  --to-date 2024-12-31 \
  --user-filter "user1@company.com,user2@company.com" \
  --max-concurrent 4 \
  --log-level DEBUG \
  --log-file extraction.log
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output-dir` | Output directory for recordings | `./zoom_recordings` |
| `-u, --user-filter` | Comma-separated user emails/IDs to filter | All users |
| `-f, --from-date` | Start date (YYYY-MM-DD) | 30 days ago |
| `-t, --to-date` | End date (YYYY-MM-DD) | Today |
| `-c, --max-concurrent` | Maximum concurrent downloads | 2 |
| `--include-trash` | Include recordings in trash | False |
| `--dry-run` | Don't download, just show what would be done | False |
| `-l, --log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `--log-file` | Log file path (optional) | Console only |
| `--resume` | Resume previous extraction | False |

### Examples

#### Extract all recordings from last 6 months
```bash
python zoom_extract.py --from-date 2024-06-01
```

#### Extract specific user's recordings
```bash
python zoom_extract.py --user-filter "john.doe@company.com"
```

#### Dry run to see what would be downloaded
```bash
python zoom_extract.py --dry-run --log-level DEBUG
```

#### Resume interrupted extraction
```bash
python zoom_extract.py --resume
```

## Directory Structure

The extractor creates an organized directory structure:

```
<ZOOM_OUTDIR>/
├── _metadata/
│   ├── extraction_state.json    # Extraction progress state
│   └── extraction_state.bak     # Backup of state file
├── _logs/
│   ├── inventory.jsonl          # Detailed file inventory (JSONL)
│   └── inventory.db             # SQLite database for inventory
└── <user-email-or-id>/
    └── <YYYYMMDD_HHMMSSZ>_<meeting_topic>_<meetingID>/
        ├── 20241201_140000Z_MP4.mp4           # Recording files
        ├── 20241201_140000Z_M4A.m4a
        ├── 20241201_140000Z_CHAT.txt
        ├── 20241201_140000Z_TRANSCRIPT.vtt
        ├── meta.json                          # Meeting metadata
        └── files.csv                          # Files listing
```

### File Naming Convention

- **Recording files**: `YYYYMMDD_HHMMSSZ_<FILETYPE>.<ext>`
- **Meeting folders**: `YYYYMMDD_HHMMSSZ_<topic>_<meetingID>`
- **User folders**: User email (sanitized for filesystem safety)

## Features in Detail

### Resumable Downloads

- **State Tracking**: Saves progress to `_metadata/extraction_state.json`
- **File Validation**: Skips files that already exist with correct size
- **Resume Support**: Can resume from where it left off after interruption
- **Crash Recovery**: Handles unexpected shutdowns gracefully

### Rate Limiting & Retries

- **Exponential Backoff**: Automatically handles rate limiting
- **Retry Logic**: Retries failed requests with increasing delays
- **Concurrent Control**: Limits concurrent downloads to avoid API limits
- **429 Handling**: Respects `Retry-After` headers from Zoom

### Edge Cases Handled

- **Trash Recordings**: Detects and reports recordings in trash
- **Passcode Protection**: Handles recordings requiring passcodes
- **UUID Encoding**: Properly handles UUIDs with forward slashes
- **File Validation**: Validates file sizes and checksums
- **Retention Policies**: Warns about old recordings that may be deleted
- **Account Restrictions**: Checks for user/account limitations

### Authentication Methods

The extractor tries multiple authentication methods:

1. **Authorization Header** (preferred)
2. **Query Parameter** (fallback)

This handles variations in Zoom's download URL behavior across different tenants.

## Monitoring & Logging

### Progress Tracking

The extractor provides real-time progress updates:

```
Progress: 1,234/5,678 files processed (21.7%)
Users processed: 45/150
Meetings processed: 892/3,456
Files downloaded: 1,156
Files skipped: 78
Files failed: 12
```

### Log Files

- **Console Output**: Real-time progress and status
- **Log File** (optional): Detailed logging to file
- **Inventory**: JSONL format with all file details
- **State File**: JSON format for resumption

### Inventory Database

The extractor creates a SQLite database (`_logs/inventory.db`) for efficient querying:

```sql
-- Get all files for a user
SELECT * FROM inventory WHERE user_email = 'user@company.com';

-- Get failed downloads
SELECT * FROM inventory WHERE status = 'failed';

-- Get files by type
SELECT * FROM inventory WHERE file_type = 'mp4';
```

## Troubleshooting

### Common Issues

#### Authentication Errors
- Verify your S2S OAuth app has correct scopes
- Check that `ZOOM_ACCOUNT_ID`, `ZOOM_CLIENT_ID`, and `ZOOM_CLIENT_SECRET` are correct
- Ensure the app is approved for your account

#### Permission Errors
- Check if your account has admin privileges
- Verify recording permissions at account/group/user level
- Some organizations restrict who can download recordings

#### Download Failures
- Check network connectivity
- Verify Zoom's download URLs are accessible
- Some recordings may be in trash and need to be restored
- Old recordings may be affected by retention policies

#### Rate Limiting
- The extractor handles this automatically
- Reduce `MAX_CONCURRENT_DOWNLOADS` if you hit limits frequently
- Check Zoom's API limits for your account type

### Debug Mode

Run with debug logging to see detailed information:

```bash
python zoom_extract.py --log-level DEBUG --log-file debug.log
```

### Dry Run

Test your configuration without downloading:

```bash
python zoom_extract.py --dry-run --log-level DEBUG
```

## Performance Tips

### Optimization

- **Concurrent Downloads**: Increase `MAX_CONCURRENT_DOWNLOADS` for faster downloads (but respect API limits)
- **Date Ranges**: Use smaller date ranges for faster processing
- **User Filtering**: Filter to specific users if you don't need all recordings

### Storage Considerations

- **Large Files**: MP4 recordings can be several GB each
- **Total Size**: Estimate ~100-500MB per hour of recording
- **Disk Space**: Ensure sufficient free space before starting

## API Limits

Zoom has rate limits that vary by account type:

- **Free/Basic**: 10 requests per second
- **Pro/Business**: 100 requests per second  
- **Enterprise**: 500 requests per second

The extractor automatically handles these limits with exponential backoff.

## Security

- **Credentials**: Never commit `.env` files to version control
- **Tokens**: OAuth tokens are cached securely and automatically refreshed
- **File Permissions**: Downloaded files inherit system permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the logs for error messages
3. Open an issue on GitHub with:
   - Error messages
   - Configuration (without credentials)
   - Log output (if applicable)

## Changelog

### v1.0.0
- Initial release
- Complete Zoom recordings extraction
- Resumable downloads
- Rate limiting and retry logic
- Edge case handling
- Comprehensive logging and inventory
