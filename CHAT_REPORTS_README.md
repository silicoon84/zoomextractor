# Zoom Chat Reports Extraction

This script extracts chat messages using the **Zoom Reports API**, which provides comprehensive access to all chat activity in your organization.

## Why Use Reports API?

The Reports API is much more reliable than individual chat endpoints because:

- ✅ **Comprehensive Coverage**: Gets ALL chat sessions and messages
- ✅ **Complete Message Data**: Includes edited, deleted, and bot messages
- ✅ **File Attachments**: Downloads file metadata and URLs
- ✅ **Reactions & Rich Text**: Captures emoji reactions and formatting
- ✅ **Session Management**: Properly handles chat sessions and channels
- ✅ **No Scope Issues**: Uses standard report permissions

## Prerequisites

- **Zoom Plan**: Pro or higher
- **Required Scopes**: 
  - `report_chat:read:admin`
  - `imchat:read:admin`
- **Granular Scopes**: `report:read:list_chat_sessions:admin`
- **Rate Limit**: MEDIUM

## Usage

### Basic Usage

```bash
# Extract chat reports for last 30 days
python extract_chat_reports.py --from-date 2024-09-01 --to-date 2024-10-01

# Extract with custom output directory
python extract_chat_reports.py --from-date 2024-01-01 --to-date 2024-02-01 --output-dir ./my_chat_reports
```

### Advanced Options

```bash
# Exclude certain message types
python extract_chat_reports.py --from-date 2024-09-01 --to-date 2024-10-01 \
    --no-edited --no-deleted --no-bot --no-reactions

# Extract for specific date range
python extract_chat_reports.py --from-date 2024-06-01 --to-date 2024-08-31
```

### Test the API

```bash
# Test if the Reports API is working
python test_chat_reports.py
```

## Output Structure

```
zoom_chat_reports/
├── sessions/                    # Complete session data
│   ├── session1_Channel_One.json
│   ├── session2_Team_Chat.json
│   └── ...
├── messages/                    # Message files
│   ├── session1_messages.json   # Regular messages
│   ├── session1_edited.json     # Edited messages
│   ├── session1_deleted.json    # Deleted messages
│   └── ...
└── _metadata/                   # Summary data
    ├── extraction_summary.json  # Overall statistics
    └── sessions_summary.json    # Session overview
```

## Message Data Structure

Each message includes:

```json
{
  "id": "7ba4d98b-0a6a-4fb4-a71b-dd13fd689dc8",
  "message": "How are you",
  "sender": "jchill@example.com",
  "sender_display_name": "Tom",
  "receiver": "jchill@example.com",
  "date_time": "2022-03-17T08:27:57Z",
  "timestamp": 1647494500135,
  "files": [...],                # File attachments
  "reactions": [...],            # Emoji reactions
  "giphy_information": [...],    # Giphy content
  "rich_text": [...],            # Text formatting
  "bot_message": {...},          # Bot messages
  "is_sender_external": true,    # External participants
  "reply_main_message_id": "...", # Thread replies
  "forward_id": "..."            # Forwarded messages
}
```

## Session Types

The API returns different session types:

- **1:1**: One-on-one direct messages
- **Group**: Group chat conversations  
- **Channel**: Public/private channels
- **Meeting**: In-meeting chat (if available)

## Date Range Limitations

- **Monthly Chunks**: The Reports API requires monthly date ranges
- **6 Month Limit**: Data is only available for the last 6 months
- **Automatic Splitting**: The script automatically splits longer ranges into monthly chunks

## File Attachments

The API provides download URLs for file attachments:

```json
{
  "files": [
    {
      "file_id": "qreigNgqTk24RNnGJDxpDg",
      "file_name": "document.pdf",
      "file_size": 224251,
      "download_url": "https://zoom.us/file/download/..."
    }
  ]
}
```

## Error Handling

The script includes robust error handling:

- ✅ **Rate Limiting**: Automatic rate limit compliance
- ✅ **Retry Logic**: Handles temporary API failures
- ✅ **Monthly Processing**: Continues if one month fails
- ✅ **Session Recovery**: Skips problematic sessions
- ✅ **Progress Logging**: Detailed progress information

## Comparison with Chat API

| Feature | Chat API | Reports API |
|---------|----------|-------------|
| **Coverage** | Limited by scopes | Complete organization |
| **Session Data** | Individual calls | Bulk session listing |
| **Message Types** | Basic messages | All types (edited/deleted/bot) |
| **File Attachments** | Limited | Complete with URLs |
| **Reliability** | Scope-dependent | Standard permissions |
| **Rate Limits** | Multiple endpoints | Single endpoint |

## Troubleshooting

### Common Issues

1. **"No chat sessions found"**
   - Check if your organization has chat activity in the date range
   - Verify you have the required scopes
   - Ensure your Zoom plan supports chat reports

2. **"Authentication failed"**
   - Verify your `.env` file has correct credentials
   - Check that your app has the required scopes
   - Ensure your token hasn't expired

3. **"Rate limit exceeded"**
   - The script includes automatic rate limiting
   - For large extractions, it may take time to complete
   - Consider reducing the date range

### Testing

```bash
# Test authentication and basic API access
python test_chat_reports.py

# Test with a small date range first
python extract_chat_reports.py --from-date 2024-10-01 --to-date 2024-10-02
```

## Environment Variables

Required in your `.env` file:

```env
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
```

## Next Steps

After extracting chat reports, you can:

1. **Analyze Message Patterns**: Process the JSON files to understand communication patterns
2. **Download Files**: Use the download URLs to retrieve file attachments
3. **Export to Other Formats**: Convert JSON to CSV, Excel, or database formats
4. **Integrate with Analytics**: Feed the data into business intelligence tools

This approach provides the most comprehensive and reliable way to extract all chat data from your Zoom organization.
