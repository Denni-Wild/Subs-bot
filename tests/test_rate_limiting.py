#!/usr/bin/env python3
"""
Test script for rate limiting functionality
"""

import asyncio
import time
from bot import rate_limit_check, global_rate_limit_check, get_transcript_with_retry, get_available_transcripts_with_retry

async def test_rate_limiting():
    """Test the rate limiting functionality"""
    print("🧪 Testing Rate Limiting Functionality")
    print("=" * 50)
    
    # Test user rate limiting
    print("\n1. Testing User Rate Limiting:")
    user_id = 12345
    
    # First request should succeed
    result1 = await rate_limit_check(user_id)
    print(f"   First request: {'✅ PASS' if result1 else '❌ FAIL'}")
    
    # Second request within interval should fail
    result2 = await rate_limit_check(user_id)
    print(f"   Second request (immediate): {'❌ PASS (should fail)' if not result2 else '❌ FAIL (should fail)'}")
    
    # Wait and try again
    print("   Waiting 16 seconds...")
    await asyncio.sleep(16)
    result3 = await rate_limit_check(user_id)
    print(f"   Third request (after wait): {'✅ PASS' if result3 else '❌ FAIL'}")
    
    # Test global rate limiting
    print("\n2. Testing Global Rate Limiting:")
    
    # First request should succeed
    result1 = await global_rate_limit_check()
    print(f"   First global request: {'✅ PASS' if result1 else '❌ FAIL'}")
    
    # Second request immediately should fail
    result2 = await global_rate_limit_check()
    print(f"   Second global request (immediate): {'❌ PASS (should fail)' if not result2 else '❌ FAIL (should fail)'}")
    
    # Wait and try again
    print("   Waiting 3 seconds...")
    await asyncio.sleep(3)
    result3 = await global_rate_limit_check()
    print(f"   Third global request (after wait): {'✅ PASS' if result3 else '❌ FAIL'}")
    
    # Test transcript retrieval with retry (using a real video ID)
    print("\n3. Testing Transcript Retrieval with Retry:")
    test_video_id = "dQw4w9WgXcQ"  # Rick Roll - should have transcripts
    
    print("   Testing get_available_transcripts_with_retry...")
    transcripts, success, error = await get_available_transcripts_with_retry(test_video_id)
    
    if success:
        print(f"   ✅ Success: Found {len(transcripts)} transcript(s)")
        for i, transcript in enumerate(transcripts[:3]):  # Show first 3
            print(f"      {i+1}. {transcript.language} ({transcript.language_code})")
    else:
        print(f"   ❌ Failed: {error}")
    
    print("\n4. Testing Transcript Retrieval with Retry:")
    if success and transcripts:
        lang_code = transcripts[0].language_code
        print(f"   Testing get_transcript_with_retry for language: {lang_code}")
        
        transcript_data, success, error = await get_transcript_with_retry(test_video_id, [lang_code])
        
        if success:
            print(f"   ✅ Success: Retrieved {len(transcript_data)} subtitle entries")
            if transcript_data:
                print(f"      First subtitle: {transcript_data[0]['text'][:50]}...")
        else:
            print(f"   ❌ Failed: {error}")
    
    print("\n" + "=" * 50)
    print("🎉 Rate limiting tests completed!")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting()) 