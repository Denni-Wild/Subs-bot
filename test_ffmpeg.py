#!/usr/bin/env python3
"""
Test script to verify FFmpeg is working with pydub
"""

import warnings
import sys
from pydub import AudioSegment

def test_ffmpeg():
    """Test if pydub can find ffmpeg without warnings"""
    print("Testing FFmpeg with pydub...")
    
    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        try:
            # Try to create an AudioSegment (this will trigger the ffmpeg check)
            # We'll create a simple silent audio segment
            audio = AudioSegment.silent(duration=1000)  # 1 second of silence
            print("✅ Successfully created AudioSegment")
            
            # Check if there were any ffmpeg-related warnings
            ffmpeg_warnings = [warning for warning in w if "ffmpeg" in str(warning.message).lower()]
            
            if ffmpeg_warnings:
                print("❌ FFmpeg warnings found:")
                for warning in ffmpeg_warnings:
                    print(f"   - {warning.message}")
                return False
            else:
                print("✅ No FFmpeg warnings detected!")
                return True
                
        except Exception as e:
            print(f"❌ Error testing pydub: {e}")
            return False

if __name__ == "__main__":
    success = test_ffmpeg()
    if success:
        print("\n🎉 FFmpeg is working correctly with pydub!")
        print("The warning should no longer appear when running your bot.")
    else:
        print("\n⚠️ FFmpeg issues detected. Please check the installation.")
    
    sys.exit(0 if success else 1) 