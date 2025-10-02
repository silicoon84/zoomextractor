# Simple Zoom Chat Extractor

A clean, focused chat extraction script using the official Zoom Chat API endpoints.

## Endpoints Used

1. **List Channels**: `GET /v2/chat/users/{userId}/channels`
   - Discovers all channels the user has access to
   - Paginated with `next_page_token`

2. **Get Messages**: `GET /v2/chat/users/{userId}/messages`
   - Works for both DMs and channel messages
   - Use `to_contact=<email>` for DMs
   - Use `to_channel=<channelId>` for channel messages
   - Supports date filtering and pagination

## Usage

### Test the API

```bash
# Test if the Chat API is working
python test_simple_chat.py
```

### List Channels

```bash
# List all channels for the authenticated user
python simple_chat_extractor.py --list-channels
```

### Extract Channel Messages

```bash
# Extract messages from a specific channel (last 30 days)
python simple_chat_extractor.py --channel channelId123

# Extract messages from a channel (last 7 days)
python simple_chat_extractor.py --channel channelId123 --days 7

# Extract without downloading files
python simple_chat_extractor.py --channel channelId123 --no-files
```

### Extract Direct Messages

```bash
# Extract messages with a specific contact (last 30 days)
python simple_chat_extractor.py --contact user@example.com

# Extract messages with a contact (last 7 days)
python simple_chat_extractor.py --contact user@example.com --days 7
```

### Extract All Users and Channels

```bash
# Extract from ALL users and their channels (last 30 days)
python simple_chat_extractor.py --all-users

# Extract from all users (last 7 days, no inactive users)
python simple_chat_extractor.py --all-users --days 7 --no-inactive

# Extract from all users without downloading files
python simple_chat_extractor.py --all-users --no-files
```

### Custom Output Directory

```bash
# Save to custom directory
python simple_chat_extractor.py --channel channelId123 --output-dir ./my_chat_data
```

## Output Structure

```
chat_extraction/
├── channels/
│   ├── user_channels.json          # List of all channels (single user)
│   ├── user_user1_channels.json    # Channels for user1
│   └── user_user2_channels.json    # Channels for user2
├── messages/
│   ├── channel_abc123_messages.json # Channel messages
│   ├── contact_user_example_com_messages.json # Contact messages
│   └── channel_xyz789_messages.json # More channel messages
├── files/
│   ├── file123_document.pdf        # Downloaded attachments
│   └── file456_image.png
└── _metadata/
    ├── user_user1_summary.json     # Summary for user1
    ├── user_user2_summary.json     # Summary for user2
    └── overall_extraction_summary.json # Overall summary
```

## Message Data Structure

Each message includes:

```json
{
  "id": "message123",
  "message": "Hello world!",
  "sender": "user@example.com",
  "date_time": "2024-01-15T10:30:00Z",
  "files": [
    {
      "file_id": "file123",
      "file_name": "document.pdf",
      "file_size": 1024,
      "download_url": "https://zoom.us/file/download/..."
    }
  ]
}
```

## Features

- ✅ **Clean API Usage**: Uses only official documented endpoints
- ✅ **File Downloads**: Automatically downloads message attachments
- ✅ **Date Filtering**: Filter messages by date range
- ✅ **Pagination**: Handles large message sets automatically
- ✅ **Rate Limiting**: Respects API rate limits
- ✅ **Error Handling**: Graceful handling of API errors
- ✅ **Flexible Output**: Organized file structure

## Prerequisites

- **Required Scopes**: `chat:read:admin` or appropriate chat permissions
- **Authentication**: Uses the same auth system as other extractors
- **Rate Limits**: MEDIUM rate limit (handled automatically)

## Examples

### Basic Channel Extraction

```bash
# List channels first
python simple_chat_extractor.py --list-channels

# Extract from a specific channel
python simple_chat_extractor.py --channel abc123def456 --days 30
```

### Contact Messages

```bash
# Extract messages with a colleague
python simple_chat_extractor.py --contact colleague@company.com --days 14
```

### Batch Processing

```bash
# Extract from multiple channels (run separately)
python simple_chat_extractor.py --channel channel1 --days 30
python simple_chat_extractor.py --channel channel2 --days 30
python simple_chat_extractor.py --channel channel3 --days 30

# Or extract from ALL users and channels at once
python simple_chat_extractor.py --all-users --days 30
```

## Error Handling

The script handles common issues:

- **No Messages Found**: Logs info and continues
- **Rate Limiting**: Automatic delays between requests
- **File Download Errors**: Logs errors but continues processing
- **Authentication Issues**: Clear error messages
- **Invalid Parameters**: Validates inputs before API calls

## File Attachments

When files are found in messages:

1. **Metadata**: File info is included in the message JSON
2. **Download**: Files are automatically downloaded to `files/` directory
3. **Naming**: Files are named as `{file_id}_{original_name}`
4. **Audio**: Supports MP4 format for audio attachments

## Date Filtering

- **Default**: Last 30 days
- **Custom Range**: Use `--days` parameter
- **Format**: ISO 8601 UTC timestamps
- **Limitation**: API may have date range limits

## Authentication

Uses the same authentication system as other extractors:

```env
# .env file
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
```

## Troubleshooting

### "No channels found"
- Check if the user has access to any channels
- Verify the user has appropriate permissions
- Try with a different user ID

### "Authentication failed"
- Verify your `.env` file is correct
- Check that your app has chat permissions
- Ensure tokens haven't expired

### "No messages found"
- Check the date range (try increasing `--days`)
- Verify the channel ID or contact email is correct
- Check if the user has permission to read those messages

### "Rate limit exceeded"
- The script includes automatic rate limiting
- For large extractions, it may take time
- Consider reducing the date range

This approach is much simpler and more reliable than the complex multi-endpoint approach!
