# Zoom Chat Messages Extractor

This module provides comprehensive extraction of all types of Zoom chat messages, including one-on-one chats, group chats, chat channels, and in-meeting chat messages from recordings.

## 🚀 Features

### **Chat Types Supported:**
- **💬 One-on-One Chats** - Direct messages between users
- **👥 Group Chats** - Multi-user chat conversations
- **📢 Chat Channels** - Organizational chat channels
- **🎥 In-Meeting Chats** - Chat messages from recorded meetings

### **Key Capabilities:**
- ✅ **Complete Chat History** - Extract all chat messages within date ranges
- ✅ **User Filtering** - Extract chats for specific users or all users
- ✅ **Date Range Filtering** - Specify custom date ranges for extraction
- ✅ **Structured Output** - Organized JSON files by chat type and user
- ✅ **Resumable Extraction** - Continue interrupted extractions
- ✅ **Rate Limiting** - Respects Zoom API rate limits
- ✅ **Error Handling** - Robust error handling and logging
- ✅ **Dry Run Mode** - Test extraction without downloading data

## 📋 Prerequisites

### **Zoom API Requirements:**
1. **Zoom Account** with admin privileges
2. **Server-to-Server OAuth App** created in Zoom Marketplace
3. **Required Scopes:**
   - `chat:read:admin` - Read chat messages
   - `user:read:admin` - Read user information
   - `recording:read:admin` - Read recording information (for meeting chats)

### **Python Dependencies:**
```bash
pip install requests python-dotenv click tqdm PyJWT python-dateutil colorama
```

## 🔧 Setup

### **1. Environment Configuration:**
Create a `.env` file with your Zoom credentials:
```env
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_FROM=2020-01-01
ZOOM_TO=2025-12-31
```

### **2. Zoom App Configuration:**
In your Zoom Marketplace app, ensure you have these scopes:
- `chat:read:admin`
- `user:read:admin`
- `recording:read:admin`
- `user:read:list_users:admin`

## 📖 Usage

### **Basic Usage:**

```bash
# Extract chat messages for a specific user
python extract_chat_messages.py --user-filter user@example.com --from-date 2020-01-01

# Extract chat messages for all users
python extract_chat_messages.py --all-users --from-date 2020-01-01

# Dry run to see what would be extracted
python extract_chat_messages.py --all-users --from-date 2020-01-01 --dry-run

# Include in-meeting chat messages from recordings
python extract_chat_messages.py --all-users --from-date 2020-01-01 --include-meeting-chats
```

### **Advanced Usage:**

```bash
# Custom output directory and date range
python extract_chat_messages.py \
  --output-dir ./my_chat_archive \
  --user-filter user1@example.com user2@example.com \
  --from-date 2020-01-01 \
  --to-date 2024-12-31 \
  --include-inactive \
  --include-meeting-chats

# Extract only recent messages
python extract_chat_messages.py \
  --all-users \
  --from-date 2024-01-01 \
  --include-meeting-chats
```

## 🧪 Testing

### **Run Comprehensive Tests:**
```bash
# Test all functionality
python test_chat_extraction.py --test-all

# Test specific user
python test_chat_extraction.py --test-user user@example.com

# Save test results
python test_chat_extraction.py --test-all --save-results
```

### **Test Scenarios:**
- ✅ Authentication verification
- ✅ User enumeration
- ✅ Chat API endpoint accessibility
- ✅ Date range filtering
- ✅ Error handling
- ✅ User-specific extraction

## 📁 Output Structure

The extractor creates a organized directory structure:

```
zoom_chat_messages/
├── one_on_one/                    # One-on-one chat messages
│   ├── user1_example_com_one_on_one.json
│   └── user2_example_com_one_on_one.json
├── group_chats/                   # Group chat messages
│   ├── user1_example_com_groups.json
│   └── user2_example_com_groups.json
├── channels/                      # Channel messages
│   ├── user1_example_com_channels.json
│   └── user2_example_com_channels.json
├── meeting_chats/                 # In-meeting chat messages
│   ├── user1_example_com_meetings.json
│   └── user2_example_com_meetings.json
└── _metadata/                     # Extraction metadata
    ├── user1_example_com_chat_summary.json
    ├── user2_example_com_chat_summary.json
    └── extraction_summary.json
```

### **Message Format:**
```json
{
  "message": "Hello, how are you?",
  "date_time": "2024-01-15T10:30:00Z",
  "sender": "user1@example.com",
  "receiver": "user2@example.com",
  "message_type": "chat",
  "message_id": "123456789",
  "file_info": {
    "file_id": "abc123",
    "file_name": "document.pdf",
    "file_size": 1024
  }
}
```

## 🔍 API Endpoints Used

### **Chat Messages:**
- `GET /chat/users/{userId}/messages` - User's chat messages
- `GET /chat/groups/{groupId}/messages` - Group chat messages
- `GET /chat/channels/{channelId}/messages` - Channel messages

### **Chat Groups and Channels:**
- `GET /chat/users/{userId}/groups` - User's chat groups
- `GET /chat/users/{userId}/channels` - User's channels

### **Meeting Recordings:**
- `GET /users/{userId}/recordings` - User's recordings
- `GET /meetings/{meetingId}/recordings` - Meeting recording details

## ⚠️ Limitations

### **API Limitations:**
1. **Rate Limits** - Zoom API has rate limits (handled automatically)
2. **Date Range** - Large date ranges may take significant time
3. **Message History** - Zoom may not retain all historical messages
4. **Permissions** - Requires admin-level access to chat data

### **Data Limitations:**
1. **File Attachments** - File content is not downloaded, only metadata
2. **Deleted Messages** - Cannot retrieve permanently deleted messages
3. **Private Groups** - May not access all private group chats
4. **Meeting Chats** - Only available for recorded meetings

## 🛠️ Troubleshooting

### **Common Issues:**

1. **Authentication Errors:**
   ```bash
   # Test authentication
   python -c "from zoom_extractor.auth import get_auth_from_env; print('OK' if get_auth_from_env() else 'Failed')"
   ```

2. **Permission Errors:**
   - Verify your Zoom app has `chat:read:admin` scope
   - Ensure you have admin privileges
   - Check if the user has chat history enabled

3. **No Messages Found:**
   - Verify the date range includes active chat periods
   - Check if the user actually has chat messages
   - Try a broader date range

4. **Rate Limit Errors:**
   - The script automatically handles rate limits
   - Increase delays if needed by modifying the RateLimiter

### **Debug Mode:**
```bash
# Enable debug logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from extract_chat_messages import extract_all_chat_messages
extract_all_chat_messages(dry_run=True)
"
```

## 📊 Performance Considerations

### **Extraction Speed:**
- **Small accounts** (< 100 users): 10-30 minutes
- **Medium accounts** (100-1000 users): 1-3 hours
- **Large accounts** (> 1000 users): 3-8 hours

### **Storage Requirements:**
- **Chat messages**: ~1-5 KB per message
- **File metadata**: ~0.5 KB per attachment
- **Meeting chats**: Varies by meeting length

### **Optimization Tips:**
1. Use specific date ranges to reduce extraction time
2. Filter by specific users when possible
3. Run during off-peak hours to avoid rate limits
4. Use dry-run mode to estimate scope

## 🔐 Security Considerations

1. **Credentials** - Store `.env` file securely
2. **Output Data** - Chat messages may contain sensitive information
3. **Access Control** - Limit access to extracted chat data
4. **Retention** - Implement appropriate data retention policies

## 📈 Future Enhancements

- **Real-time Monitoring** - Webhook-based chat monitoring
- **Advanced Filtering** - Message content filtering
- **Export Formats** - CSV, Excel, PDF export options
- **Analytics** - Chat activity analytics and reporting
- **Search** - Full-text search across extracted messages

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Run the test script: `python test_chat_extraction.py --test-all`
3. Review the logs for specific error messages
4. Verify your Zoom app configuration and scopes

---

**Note:** This tool is designed for legitimate administrative and archival purposes. Ensure compliance with your organization's data policies and applicable laws when extracting chat messages.
