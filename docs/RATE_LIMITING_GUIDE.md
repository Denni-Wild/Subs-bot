# Rate Limiting and Error Handling Guide

## Overview

This guide explains the enhanced rate limiting and error handling implemented to solve the "Too Many Requests" error from YouTube's transcript API.

## Problem Solved

### Original Issue
```
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=429 
Client Error: Too Many Requests for url: https://www.youtube.com/api/timedtext...
```

### Root Causes
1. **YouTube API Rate Limits**: YouTube has strict limits on transcript requests
2. **No Retry Logic**: Original code failed immediately on 429 errors
3. **No Exponential Backoff**: No progressive delay between retries
4. **Concurrent Requests**: Multiple simultaneous requests triggered rate limits

## Solution Implemented

### 1. Enhanced Rate Limiting Constants

```python
# Enhanced rate limiting constants
MIN_REQUEST_INTERVAL = 15  # Increased from 10 to 15 seconds
MAX_RETRIES = 3
BASE_DELAY = 2  # Base delay in seconds
MAX_DELAY = 60  # Maximum delay in seconds
```

### 2. Multi-Level Rate Limiting

#### User-Level Rate Limiting
- **Purpose**: Prevent individual users from making too many requests
- **Implementation**: Tracks last request time per user ID
- **Limit**: 15 seconds between requests per user

#### Global Rate Limiting
- **Purpose**: Prevent API abuse across all users
- **Implementation**: Global lock with minimum 2-second intervals
- **Benefit**: Protects against concurrent requests

### 3. Exponential Backoff Retry Logic

```python
async def get_transcript_with_retry(video_id: str, languages: list, max_retries: int = MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            # Check global rate limit
            if not await global_rate_limit_check():
                await asyncio.sleep(2)
                continue
                
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            return transcript, True, None
            
        except Exception as e:
            if "Too Many Requests" in str(e) or "429" in str(e):
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = min(BASE_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_DELAY)
                    await asyncio.sleep(delay)
                    continue
                else:
                    return None, False, "Превышен лимит запросов к YouTube. Попробуйте позже (через 5-10 минут)."
```

### 4. Improved Error Messages

The system now provides specific, user-friendly error messages:

- **Rate Limit**: "Превышен лимит запросов к YouTube. Попробуйте позже (через 5-10 минут)."
- **Disabled Transcripts**: "У этого видео субтитры отключены."
- **No Transcripts**: "Субтитры не найдены для этого видео."
- **Unavailable Video**: "Видео недоступно или удалено."

## Key Features

### 1. Progressive Delays
- **Attempt 1**: 2-3 seconds delay
- **Attempt 2**: 4-5 seconds delay  
- **Attempt 3**: 8-9 seconds delay
- **Maximum**: 60 seconds

### 2. Jitter Implementation
- Adds random delay (0-1 seconds) to prevent thundering herd
- Helps distribute requests more evenly

### 3. Request Queuing
- Global lock prevents concurrent API calls
- Ensures minimum 2-second intervals between any requests

### 4. User Feedback
- Processing messages show current status
- Clear error messages with actionable advice
- Remaining time display for rate limits

## Testing

Run the test script to verify rate limiting functionality:

```bash
python test_rate_limiting.py
```

This will test:
- User rate limiting
- Global rate limiting  
- Transcript retrieval with retry logic
- Error handling

## Best Practices

### For Users
1. **Wait Between Requests**: Don't make requests faster than every 15 seconds
2. **Be Patient**: Rate limit errors are temporary, wait 5-10 minutes
3. **Check Video**: Ensure the video has available transcripts

### For Developers
1. **Monitor Logs**: Watch for rate limit warnings in logs
2. **Adjust Limits**: Modify constants if needed for your use case
3. **Test Thoroughly**: Use the test script before deployment

## Configuration

You can adjust the rate limiting behavior by modifying these constants in `bot.py`:

```python
MIN_REQUEST_INTERVAL = 15  # User rate limit (seconds)
MAX_RETRIES = 3           # Maximum retry attempts
BASE_DELAY = 2            # Base delay for exponential backoff
MAX_DELAY = 60            # Maximum delay (seconds)
```

## Troubleshooting

### Common Issues

1. **Still Getting Rate Limits**
   - Increase `MIN_REQUEST_INTERVAL` to 20-30 seconds
   - Increase `MAX_DELAY` to 120 seconds
   - Check if multiple users are making requests simultaneously

2. **Slow Response Times**
   - Decrease `BASE_DELAY` to 1 second
   - Decrease `MAX_DELAY` to 30 seconds
   - Monitor if this causes more rate limit errors

3. **Memory Issues**
   - The `request_timestamps` dictionary grows with users
   - Consider implementing cleanup for old entries
   - Monitor memory usage in production

### Monitoring

Add these log statements to monitor rate limiting:

```python
logger.info(f"Rate limit hit for user {user_id}, waiting {delay}s")
logger.warning(f"Global rate limit active, requests queued")
logger.info(f"Successful transcript retrieval after {attempts} attempts")
```

## Future Improvements

1. **Redis Integration**: Use Redis for distributed rate limiting
2. **Adaptive Limits**: Adjust limits based on API response patterns
3. **Request Pooling**: Implement request batching for efficiency
4. **Metrics Collection**: Track rate limit frequency and success rates

## Conclusion

This enhanced rate limiting system should eliminate the "Too Many Requests" errors while providing a better user experience with clear feedback and automatic retry logic. 