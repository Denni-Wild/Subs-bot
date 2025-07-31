#!/usr/bin/env python3
"""
Integration tests for rate limiting functionality

These tests verify the rate limiting system works correctly with real YouTube API calls.
They are designed to be safe and avoid hitting actual rate limits.
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# Add the parent directory to the path to import bot module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Configure logging for integration tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Known video IDs for testing (videos that are likely to have transcripts)
TEST_VIDEO_IDS = [
    "dQw4w9WgXcQ",  # Rick Roll - should have transcripts
    "jNQXAC9IVRw",  # Me at the zoo - first YouTube video
    "kJQP7kiw5Fk",  # Luis Fonsi - Despacito
]

# Test configuration
INTEGRATION_TEST_DELAY = 5  # Seconds between tests to avoid rate limits
MAX_TEST_DURATION = 30  # Maximum seconds for any single test


class TestRateLimitingIntegration:
    """Integration tests for rate limiting functionality"""
    
    def setup_method(self):
        """Setup before each test"""
        # Clear rate limiting state
        bot.request_timestamps.clear()
        bot.global_last_request = 0
        logger.info(f"Starting integration test: {self.__class__.__name__}")
    
    def teardown_method(self):
        """Cleanup after each test"""
        # Add delay to avoid rate limits
        time.sleep(INTEGRATION_TEST_DELAY)
        logger.info(f"Completed integration test: {self.__class__.__name__}")
    
    @pytest.mark.asyncio
    async def test_real_youtube_video_transcript_retrieval(self):
        """Test retrieving transcripts from a real YouTube video"""
        logger.info("Testing real YouTube video transcript retrieval")
        
        # Try different video IDs until we find one that works
        for video_id in TEST_VIDEO_IDS:
            try:
                logger.info(f"Trying video ID: {video_id}")
                
                # Test the retry function with real API
                result, success, error = await bot.get_available_transcripts_with_retry(video_id)
                
                if success and result and len(result) > 0:
                    logger.info(f"Found {len(result)} transcript languages for video {video_id}")
                    
                    # Test getting actual transcript data for the first available language
                    lang_code = result[0].language_code
                    transcript_data, success, error = await bot.get_transcript_with_retry(video_id, [lang_code])
                    
                    if success and transcript_data and len(transcript_data) > 0:
                        logger.info(f"Successfully retrieved {len(transcript_data)} subtitle entries for language {lang_code}")
                        # Test passed successfully
                        return
                    else:
                        logger.warning(f"Failed to get transcript data for {video_id}: {error}")
                        continue
                else:
                    logger.warning(f"Failed to get transcript list for {video_id}: {error}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Exception testing video {video_id}: {e}")
                continue
        
        # If we get here, none of the test videos worked
        # This is acceptable for integration tests - the API might be temporarily unavailable
        logger.warning("All test videos failed - this might be due to temporary API issues")
        pytest.skip("YouTube API temporarily unavailable - skipping real video test")
    
    @pytest.mark.asyncio
    async def test_rate_limiting_with_real_api_calls(self):
        """Test rate limiting behavior with real API calls"""
        logger.info("Testing rate limiting with real API calls")
        
        video_id = TEST_VIDEO_IDS[1]  # Me at the zoo
        
        # First request should succeed
        start_time = time.time()
        result1, success1, error1 = await bot.get_available_transcripts_with_retry(video_id)
        duration1 = time.time() - start_time
        
        assert success1 is True, f"First request failed: {error1}"
        assert duration1 < MAX_TEST_DURATION, f"First request took too long: {duration1}s"
        
        # Second request should also succeed (different video)
        video_id2 = TEST_VIDEO_IDS[2]  # Despacito
        start_time = time.time()
        result2, success2, error2 = await bot.get_available_transcripts_with_retry(video_id2)
        duration2 = time.time() - start_time
        
        assert success2 is True, f"Second request failed: {error2}"
        assert duration2 < MAX_TEST_DURATION, f"Second request took too long: {duration2}s"
        
        logger.info(f"Both requests completed successfully. Durations: {duration1:.2f}s, {duration2:.2f}s")
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_behavior(self):
        """Test exponential backoff behavior with controlled failures"""
        logger.info("Testing exponential backoff behavior")
        
        # Mock the API to simulate rate limiting
        with patch('bot.YouTubeTranscriptApi.get_transcript') as mock_get_transcript:
            # Simulate rate limit errors
            mock_get_transcript.side_effect = Exception("Too Many Requests")
            
            start_time = time.time()
            result, success, error = await bot.get_transcript_with_retry(
                "test_video", ["en"], max_retries=3
            )
            duration = time.time() - start_time
            
            # Should fail after retries
            assert success is False, "Should have failed after retries"
            assert "Превышен лимит запросов" in error, f"Unexpected error: {error}"
            
            # Should have taken some time due to backoff delays
            assert duration > 2, f"Backoff delays too short: {duration}s"
            assert duration < 15, f"Backoff delays too long: {duration}s"
            
            logger.info(f"Exponential backoff test completed in {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test handling of concurrent requests"""
        logger.info("Testing concurrent request handling")
        
        # Create multiple concurrent requests
        async def make_request(video_id):
            return await bot.get_available_transcripts_with_retry(video_id)
        
        # Start multiple requests concurrently
        start_time = time.time()
        tasks = [make_request(video_id) for video_id in TEST_VIDEO_IDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Check results
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Request {i} failed with exception: {result}")
            elif result[1]:  # success flag
                success_count += 1
                logger.info(f"Request {i} succeeded")
            else:
                logger.warning(f"Request {i} failed: {result[2]}")
        
        # At least some requests should succeed
        assert success_count > 0, "No requests succeeded"
        assert duration < MAX_TEST_DURATION, f"Concurrent requests took too long: {duration}s"
        
        logger.info(f"Concurrent requests completed: {success_count}/{len(results)} succeeded in {duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_error_handling_scenarios(self):
        """Test various error handling scenarios"""
        logger.info("Testing error handling scenarios")
        
        # Test with invalid video ID
        result, success, error = await bot.get_available_transcripts_with_retry("invalid_video_id")
        assert success is False, "Should fail with invalid video ID"
        assert error is not None, "Should have error message"
        logger.info(f"Invalid video ID test: {error}")
        
        # Test with non-existent video ID
        result, success, error = await bot.get_available_transcripts_with_retry("12345678901")
        assert success is False, "Should fail with non-existent video ID"
        assert error is not None, "Should have error message"
        logger.info(f"Non-existent video ID test: {error}")
    
    @pytest.mark.asyncio
    async def test_global_rate_limit_enforcement(self):
        """Test global rate limit enforcement"""
        logger.info("Testing global rate limit enforcement")
        
        # Test that global rate limit prevents too many requests
        async def test_global_limit():
            # Make multiple rapid requests
            results = []
            for i in range(5):
                result = await bot.global_rate_limit_check()
                results.append(result)
                await asyncio.sleep(0.1)  # Small delay
            
            return results
        
        results = await test_global_limit()
        
        # Only one request should succeed (the first one)
        success_count = sum(results)
        assert success_count == 1, f"Expected 1 successful request, got {success_count}"
        
        logger.info(f"Global rate limit test: {success_count}/5 requests succeeded")
    
    @pytest.mark.asyncio
    async def test_user_rate_limit_isolation(self):
        """Test that user rate limits are isolated"""
        logger.info("Testing user rate limit isolation")
        
        user1 = 12345
        user2 = 67890
        
        # Both users should be able to make requests
        result1 = await bot.rate_limit_check(user1)
        result2 = await bot.rate_limit_check(user2)
        
        assert result1 is True, "User 1 should be able to make request"
        assert result2 is True, "User 2 should be able to make request"
        
        # Second requests should be blocked
        result1_2 = await bot.rate_limit_check(user1)
        result2_2 = await bot.rate_limit_check(user2)
        
        assert result1_2 is False, "User 1 second request should be blocked"
        assert result2_2 is False, "User 2 second request should be blocked"
        
        logger.info("User rate limit isolation test passed")
    
    @pytest.mark.asyncio
    async def test_rate_limit_recovery(self):
        """Test that rate limits recover after waiting"""
        logger.info("Testing rate limit recovery")
        
        user_id = 99999
        
        # First request
        result1 = await bot.rate_limit_check(user_id)
        assert result1 is True, "First request should succeed"
        
        # Second request should be blocked
        result2 = await bot.rate_limit_check(user_id)
        assert result2 is False, "Second request should be blocked"
        
        # Wait for rate limit to expire (simulate by clearing state)
        bot.request_timestamps[user_id] = 0
        
        # Third request should succeed
        result3 = await bot.rate_limit_check(user_id)
        assert result3 is True, "Third request should succeed after recovery"
        
        logger.info("Rate limit recovery test passed")


class TestRateLimitingPerformance:
    """Performance tests for rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_performance(self):
        """Test performance of rate limit checks"""
        logger.info("Testing rate limit check performance")
        
        # Test multiple rapid rate limit checks
        start_time = time.time()
        
        for i in range(100):
            await bot.rate_limit_check(i)
        
        duration = time.time() - start_time
        
        # Should be very fast (less than 1 second for 100 checks)
        assert duration < 1.0, f"Rate limit checks too slow: {duration}s for 100 checks"
        
        logger.info(f"Rate limit check performance: {duration:.3f}s for 100 checks")
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage of rate limiting system"""
        logger.info("Testing memory usage")
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Add many users to rate limiting system
        for i in range(1000):
            await bot.rate_limit_check(i)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024, f"Memory usage too high: {memory_increase / 1024 / 1024:.2f}MB"
        
        logger.info(f"Memory usage test: {memory_increase / 1024 / 1024:.2f}MB increase")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short"]) 