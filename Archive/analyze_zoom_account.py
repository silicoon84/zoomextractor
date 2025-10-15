#!/usr/bin/env python3
"""
Zoom Account Analysis Script

Analyzes your Zoom account to show:
- Total users
- Total recordings across time periods
- File types and sizes
- Storage requirements
- Time distribution of recordings
"""

import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import our modules
from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator

def format_size(bytes_size):
    """Format bytes into human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def analyze_account():
    """Analyze the Zoom account."""
    print("🔍 Analyzing Zoom Account...")
    print("=" * 60)
    
    try:
        # Initialize auth
        auth = get_auth_from_env()
        headers = auth.get_auth_headers()
        
        # Initialize components
        user_enumerator = UserEnumerator(headers)
        recordings_lister = RecordingsLister(headers)
        
        # 1. Analyze Users
        print("\n👥 USER ANALYSIS")
        print("-" * 30)
        
        # Get all users (active + inactive for comprehensive coverage)
        active_users = list(user_enumerator.list_all_users(user_type="active"))
        inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
        users = active_users + inactive_users
        print(f"Total Active Users: {len(users)}")
        
        # User type breakdown
        user_types = defaultdict(int)
        for user in users:
            user_type = user.get('type', 'unknown')
            user_types[user_type] += 1
        
        for user_type, count in user_types.items():
            print(f"  - {user_type}: {count}")
        
        # 2. Analyze Recordings by Time Periods
        print("\n📅 RECORDING ANALYSIS BY TIME PERIOD")
        print("-" * 40)
        
        # Define time periods to analyze
        time_periods = [
            ("Last 7 days", 7),
            ("Last 30 days", 30),
            ("Last 90 days", 90),
            ("Last 6 months", 180),
            ("Last year", 365),
            ("All time (2024)", None)
        ]
        
        total_meetings = 0
        total_files = 0
        total_size = 0
        file_types = defaultdict(int)
        monthly_stats = defaultdict(lambda: {'meetings': 0, 'files': 0, 'size': 0})
        
        for period_name, days in time_periods:
            print(f"\n{period_name}:")
            
            if days:
                # Calculate date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                date_generator = DateWindowGenerator(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            else:
                # Full year 2024
                date_generator = DateWindowGenerator('2024-01-01', '2024-12-31')
            
            period_meetings = 0
            period_files = 0
            period_size = 0
            
            # Sample users (first 10 for analysis)
            sample_users = users[:10]
            
            for user in sample_users:
                user_id = user["id"]
                user_email = user.get("email", "unknown")
                
                for start_date, end_date in date_generator.generate_monthly_windows():
                    try:
                        meetings = list(recordings_lister.list_user_recordings(
                            user_id, start_date, end_date, include_trash=True
                        ))
                        
                        for meeting in meetings:
                            period_meetings += 1
                            processed_files = meeting.get("processed_files", [])
                            
                            for file_info in processed_files:
                                period_files += 1
                                file_size = file_info.get("file_size", 0)
                                period_size += file_size
                                
                                file_type = file_info.get("file_type", "unknown")
                                file_types[file_type] += 1
                                
                                # Monthly stats
                                month_key = start_date.strftime('%Y-%m')
                                monthly_stats[month_key]['meetings'] += 1
                                monthly_stats[month_key]['files'] += 1
                                monthly_stats[month_key]['size'] += file_size
                    
                    except Exception as e:
                        print(f"    Error processing {user_email}: {e}")
                        continue
            
            # Scale up results (since we only sampled 10 users)
            if len(sample_users) > 0 and len(users) > 0:
                scale_factor = len(users) / len(sample_users)
                period_meetings = int(period_meetings * scale_factor)
                period_files = int(period_files * scale_factor)
                period_size = int(period_size * scale_factor)
            
            print(f"  📊 Estimated Meetings: {period_meetings:,}")
            print(f"  📁 Estimated Files: {period_files:,}")
            print(f"  💾 Estimated Size: {format_size(period_size)}")
            
            total_meetings += period_meetings
            total_files += period_files
            total_size += period_size
        
        # 3. File Type Analysis
        print("\n📁 FILE TYPE BREAKDOWN")
        print("-" * 25)
        for file_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {file_type}: {count:,} files")
        
        # 4. Monthly Distribution
        print("\n📊 MONTHLY DISTRIBUTION (2024)")
        print("-" * 35)
        for month in sorted(monthly_stats.keys()):
            stats = monthly_stats[month]
            print(f"  {month}: {stats['meetings']} meetings, {stats['files']} files, {format_size(stats['size'])}")
        
        # 5. Storage Requirements
        print("\n💾 STORAGE ANALYSIS")
        print("-" * 20)
        print(f"Total Estimated Meetings: {total_meetings:,}")
        print(f"Total Estimated Files: {total_files:,}")
        print(f"Total Estimated Size: {format_size(total_size)}")
        print(f"Average File Size: {format_size(total_size / max(total_files, 1))}")
        print(f"Average Files per Meeting: {total_files / max(total_meetings, 1):.1f}")
        
        # 6. Recommendations
        print("\n💡 RECOMMENDATIONS")
        print("-" * 18)
        
        if total_size > 100 * 1024**3:  # 100GB
            print("⚠️  Large dataset detected!")
            print("   - Consider extracting in smaller chunks")
            print("   - Monitor disk space closely")
            print("   - Use --max-concurrent 1 for stability")
        
        if total_meetings > 1000:
            print("📈 High volume of meetings")
            print("   - Extraction will take several hours")
            print("   - Consider running overnight")
            print("   - Use --log-file for monitoring")
        
        print("🚀 Ready to extract!")
        print("   - Start with recent data first")
        print("   - Use --dry-run to verify")
        print("   - Tool is resumable if interrupted")
        
    except Exception as e:
        print(f"❌ Error analyzing account: {e}")
        return False
    
    return True

def quick_sample():
    """Quick sample of recent recordings."""
    print("\n🔍 QUICK SAMPLE (Last 30 days, 5 users)")
    print("-" * 45)
    
    try:
        auth = get_auth_from_env()
        headers = auth.get_auth_headers()
        
        user_enumerator = UserEnumerator(headers)
        recordings_lister = RecordingsLister(headers)
        
        # Get 5 users
        # Get all users (active + inactive for comprehensive coverage)
        active_users = list(user_enumerator.list_all_users(user_type="active"))
        inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
        users = active_users + inactive_users[:5]
        
        # Last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        date_generator = DateWindowGenerator(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )
        
        total_meetings = 0
        total_files = 0
        
        for user in users:
            user_email = user.get("email", "unknown")
            user_id = user["id"]
            
            print(f"\n👤 {user_email}:")
            
            for start_date, end_date in date_generator.generate_monthly_windows():
                try:
                    meetings = list(recordings_lister.list_user_recordings(
                        user_id, start_date, end_date
                    ))
                    
                    user_meetings = len(meetings)
                    user_files = sum(len(m.get("processed_files", [])) for m in meetings)
                    
                    total_meetings += user_meetings
                    total_files += user_files
                    
                    if user_meetings > 0:
                        print(f"  📅 {start_date.strftime('%Y-%m')}: {user_meetings} meetings, {user_files} files")
                    
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                    continue
        
        print(f"\n📊 Sample Results (5 users, 30 days):")
        print(f"  Meetings: {total_meetings}")
        print(f"  Files: {total_files}")
        
        if len(users) > 0:
            scale_factor = 200 / 5  # Assuming 200 total users
            print(f"\n🔮 Projected for all users:")
            print(f"  Meetings: {int(total_meetings * scale_factor)}")
            print(f"  Files: {int(total_files * scale_factor)}")
        
    except Exception as e:
        print(f"❌ Error in quick sample: {e}")

if __name__ == "__main__":
    print("🔍 Zoom Account Analysis Tool")
    print("=" * 60)
    
    # Run quick sample first
    quick_sample()
    
    # Ask if user wants full analysis
    print("\n" + "=" * 60)
    response = input("Run full analysis? This will take several minutes (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        analyze_account()
    else:
        print("✅ Quick sample completed. Use 'python analyze_zoom_account.py' for full analysis.")
