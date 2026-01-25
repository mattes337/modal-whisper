# YouTube Transcription Service

This document provides a comprehensive guide for using the YouTube transcription endpoint in the Modal WhisperX API.

## Overview

The YouTube transcription service allows you to extract metadata, transcripts, and captions from YouTube videos. It supports multiple languages and provides detailed video information including thumbnails, view counts, and available download formats.

## Endpoint

**POST** `/v1/youtube/transcribe`

## Request Format

### Headers
```
Content-Type: application/json
```

### Request Body
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "download_video": false
}
```

### Parameters

- `url` (required): YouTube video URL or video ID
  - Supports various YouTube URL formats:
    - `https://www.youtube.com/watch?v=VIDEO_ID`
    - `https://youtu.be/VIDEO_ID`
    - `https://www.youtube.com/embed/VIDEO_ID`
    - `https://www.youtube.com/shorts/VIDEO_ID`
    - Just the video ID: `VIDEO_ID`

- `download_video` (optional): Boolean flag to download video file (default: false)
  - When true, downloads video in 720p quality and returns base64-encoded content
  - **Warning**: Video downloads consume significant bandwidth and storage

## Usage Examples

### Basic Transcription Request

```bash
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

### Request with Video Download

```bash
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtu.be/dQw4w9WgXcQ",
    "download_video": true
  }'
```

### Using Video ID Only

```bash
curl -X POST "http://localhost:8000/v1/youtube/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "dQw4w9WgXcQ"
  }'
```

## Response Format

### Successful Response

```json
{
  "success": true,
  "metadata": {
    "id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
    "description": "The official video for \"Never Gonna Give You Up\" by Rick Astley...",
    "duration": 212,
    "view_count": 1400000000,
    "like_count": 15000000,
    "upload_date": "20091025",
    "uploader": "Rick Astley",
    "uploader_id": "RickAstleyVEVO",
    "channel_url": "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "thumbnails": [
      {
        "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "width": 480,
        "height": 360
      }
    ]
  },
  "transcript": {
    "language": "en",
    "entries": [
      {
        "text": "We're no strangers to love",
        "start": 0.0,
        "duration": 3.5
      },
      {
        "text": "You know the rules and so do I",
        "start": 3.5,
        "duration": 4.2
      }
    ]
  },
  "transcript_languages": [
    {
      "language": "English",
      "language_code": "en",
      "is_generated": false,
      "is_translatable": true
    },
    {
      "language": "Spanish",
      "language_code": "es",
      "is_generated": true,
      "is_translatable": true
    }
  ],
  "formats": [
    {
      "format_id": "18",
      "ext": "mp4",
      "quality": "medium",
      "format_note": "360p",
      "filesize": 15728640,
      "width": 640,
      "height": 360,
      "fps": 30,
      "vcodec": "avc1.42001E",
      "acodec": "mp4a.40.2"
    }
  ],
  "total_formats": 15,
  "video_download": {
    "downloaded": true,
    "format": "720p mp4",
    "size_bytes": 52428800,
    "content_base64": "UklGRiQAAABXQVZFZm10IBAAAAAB..."
  }
}
```

### Response Fields Explanation

- `success`: Boolean indicating if the operation was successful
- `metadata`: Video information including title, description, view counts, etc.
- `transcript`: Transcript data with language and timed entries
  - `language`: Language code of the transcript
  - `entries`: Array of transcript segments with text, start time, and duration
- `transcript_languages`: Available transcript languages for the video
- `formats`: Available download formats with quality, codec, and file information
- `total_formats`: Total number of available formats
- `video_download` (only when `download_video: true`):
  - `downloaded`: Boolean indicating if video was downloaded
  - `format`: Video format and quality
  - `size_bytes`: File size in bytes
  - `content_base64`: Base64-encoded video content

## Error Responses

### Invalid URL Format

```json
{
  "error": "Invalid YouTube URL or video ID"
}
```

**HTTP Status**: 200 (with error in response body)

**Cause**: The provided URL is not a valid YouTube URL format or video ID.

### Video Not Found

```json
{
  "error": "Failed to extract video info: Video unavailable"
}
```

**HTTP Status**: 200 (with error in response body)

**Cause**: The video ID exists but the video is private, deleted, or region-restricted.

### No Transcript Available

```json
{
  "success": true,
  "metadata": {
    "id": "VIDEO_ID",
    "title": "Video Title",
    // ... other metadata
  },
  "transcript": {
    "error": "No transcript available: Could not retrieve a transcript for the video"
  },
  "transcript_languages": [],
  "formats": [
    // ... available formats
  ],
  "total_formats": 10
}
```

**HTTP Status**: 200

**Cause**: The video exists but has no captions or transcripts available.

### Missing URL Parameter

```json
{
  "error": "Missing 'url' parameter"
}
```

**HTTP Status**: 200 (with error in response body)

**Cause**: The request body doesn't contain the required `url` field.

### Service Unavailable

```json
{
  "error": "YouTube Modal service is not available"
}
```

**HTTP Status**: 503

**Cause**: The Modal YouTube service is not deployed or not responding.

### Rate Limiting

```json
{
  "error": "API error: Rate limit exceeded"
}
```

**HTTP Status**: 429

**Cause**: Too many requests sent in a short time period.

### Timeout Error

```json
{
  "error": "Unexpected error: Request timeout"
}
```

**HTTP Status**: 200 (with error in response body)

**Cause**: The video processing took longer than the 5-minute timeout limit.

## Best Practices

1. **URL Validation**: Always validate YouTube URLs on the client side before sending requests.

2. **Error Handling**: Implement proper error handling for all possible error responses.

3. **Video Downloads**: Use `download_video: true` sparingly as it consumes significant resources.

4. **Transcript Languages**: Check `transcript_languages` to see all available languages before requesting specific language transcripts.

5. **Rate Limiting**: Implement client-side rate limiting to avoid hitting service limits.

6. **Timeout Handling**: Set appropriate timeout values for your HTTP client (recommend 5+ minutes).

## Language Support

The service supports transcripts in multiple languages including:
- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)
- And many more...

The service will automatically attempt to retrieve English transcripts first, falling back to the first available language if English is not available.

## Limitations

- Maximum video duration: No specific limit, but longer videos may timeout
- Video download quality: Limited to 720p maximum
- Transcript availability: Depends on YouTube's caption availability
- Rate limiting: Subject to YouTube's API rate limits
- File size: Video downloads are base64 encoded, increasing payload size by ~33%

## Health Check

To verify the YouTube service is available, check the health endpoint:

```bash
curl http://localhost:8000/health
```

Look for `youtube_modal_connected: true` in the response.