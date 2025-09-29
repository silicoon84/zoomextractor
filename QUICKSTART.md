# Quick Start Guide

Get up and running with Zoom Recordings Extractor in 5 minutes.

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Create Zoom S2S OAuth App

1. Go to [Zoom Marketplace](https://marketplace.zoom.us/)
2. Click "Develop" → "Build App"
3. Choose "Server-to-Server OAuth"
4. Add these scopes:
   - `recording:read`
   - `user:read`
   - `meeting:read`
5. Copy your **Account ID**, **Client ID**, and **Client Secret**

## 3. Configure Environment

```bash
cp env.example .env
```

Edit `.env` with your credentials:
```env
ZOOM_ACCOUNT_ID=your_account_id_here
ZOOM_CLIENT_ID=your_client_id_here
ZOOM_CLIENT_SECRET=your_client_secret_here
```

## 4. Test Installation

```bash
python test_installation.py
```

## 5. Run Dry Test

```bash
python zoom_extract.py --dry-run --log-level DEBUG
```

## 6. Extract Recordings

```bash
# Extract last 30 days of recordings
python zoom_extract.py

# Extract specific date range
python zoom_extract.py --from-date 2024-01-01 --to-date 2024-12-31

# Extract specific user's recordings
python zoom_extract.py --user-filter "user@company.com"

# Extract with more concurrent downloads (faster)
python zoom_extract.py --max-concurrent 4
```

## Common Commands

```bash
# Help
python zoom_extract.py --help

# Resume interrupted extraction
python zoom_extract.py --resume

# Include recordings in trash
python zoom_extract.py --include-trash

# Save logs to file
python zoom_extract.py --log-file extraction.log

# Extract everything from 2024
python zoom_extract.py --from-date 2024-01-01 --to-date 2024-12-31
```

## Output Structure

Your recordings will be organized like this:

```
zoom_recordings/
├── user@company.com/
│   └── 20241201_140000Z_Weekly_Meeting_1234567890/
│       ├── 20241201_140000Z_MP4.mp4
│       ├── 20241201_140000Z_M4A.m4a
│       ├── 20241201_140000Z_CHAT.txt
│       ├── meta.json
│       └── files.csv
└── _metadata/
    └── extraction_state.json
```

## Troubleshooting

### Authentication Issues
- Verify your S2S OAuth app has correct scopes
- Check that credentials in `.env` are correct
- Ensure app is approved for your account

### Permission Issues
- Check if you have admin privileges
- Verify recording permissions at account level
- Some orgs restrict who can download recordings

### Rate Limiting
- The tool handles this automatically
- Reduce `--max-concurrent` if you hit limits frequently

### Network Issues
- Check your internet connection
- Some recordings may be in trash (use `--include-trash`)
- Old recordings may be affected by retention policies

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [example_usage.py](example_usage.py) for programmatic usage
- Run `python zoom_extract.py --help` for all options

## Support

If you encounter issues:
1. Check the troubleshooting section
2. Run with `--log-level DEBUG` for detailed logs
3. Open an issue on GitHub with error details
