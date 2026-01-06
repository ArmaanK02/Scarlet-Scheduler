"""
Integrated Workflow: Scrape and Update Course Data
Runs the scraper, converts the data, and updates the bot's database
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import subprocess

# Import scraper functions
from course_json_scraper import (
    SUBJECT_CODES, get_semester_code, scrape_course_data
)
from data_converter import convert_api_data_to_bot_format


def get_current_semester() -> tuple[str, str]:
    """Determine current semester based on date"""
    now = datetime.now()
    month = now.month
    year = str(now.year)
    
    # Spring: January - May (semester code: 1YYYY)
    # Fall: September - December (semester code: 9YYYY)
    if 1 <= month <= 5:
        return year, "spring"
    else:
        return year, "fall"


def scrape_all_courses(year: str = None, semester: str = None, 
                       campus: str = "NB", level: str = "UG",
                       progress_callback=None) -> list:
    """
    Scrape all courses from all subjects.
    
    Args:
        year: Year (e.g., "2026")
        semester: "spring" or "fall"
        campus: Campus code (default: "NB")
        level: Level code (default: "UG")
        progress_callback: Optional function(callback(current, total, subject))
    
    Returns:
        List of all courses
    """
    if not year or not semester:
        year, semester = get_current_semester()
    
    semester_code = get_semester_code(year, semester)
    
    print(f"📡 Scraping courses for {semester.capitalize()} {year}...")
    print(f"   Semester code: {semester_code}")
    print(f"   Campus: {campus}, Level: {level}")
    print(f"   Subjects: {len(SUBJECT_CODES)}")
    print()
    
    all_courses = []
    successful = 0
    failed = 0
    
    for i, subject_code in enumerate(SUBJECT_CODES, 1):
        if progress_callback:
            progress_callback(i, len(SUBJECT_CODES), subject_code)
        
        try:
            courses = scrape_course_data(subject_code, semester_code, campus, level)
            if courses:
                all_courses.extend(courses)
                successful += 1
                print(f"  [{i}/{len(SUBJECT_CODES)}] {subject_code}: ✓ {len(courses)} courses")
            else:
                failed += 1
                print(f"  [{i}/{len(SUBJECT_CODES)}] {subject_code}: ✗ No data")
        except Exception as e:
            failed += 1
            print(f"  [{i}/{len(SUBJECT_CODES)}] {subject_code}: ✗ Error: {e}")
        
        # Small delay to avoid overwhelming server
        import time
        time.sleep(0.3)
    
    print()
    print(f"✓ Scraping complete: {successful} successful, {failed} failed")
    print(f"  Total courses: {len(all_courses)}")
    
    return all_courses


def update_bot_data(year: str = None, semester: str = None,
                    campus: str = "NB", level: str = "UG",
                    output_file: str = "rutgers_scheduler_data.json",
                    backup: bool = True) -> bool:
    """
    Complete workflow: scrape courses and update bot data.
    
    Args:
        year: Year (auto-detected if None)
        semester: "spring" or "fall" (auto-detected if None)
        campus: Campus code
        level: Level code
        output_file: Output JSON file path
        backup: Whether to backup existing file
    
    Returns:
        True if successful
    """
    print("=" * 70)
    print(" " * 20 + "COURSE DATA UPDATER")
    print("=" * 70)
    print()
    
    # Backup existing file
    output_path = Path(output_file)
    if backup and output_path.exists():
        backup_path = output_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print(f"📦 Backing up existing data to {backup_path.name}...")
        import shutil
        shutil.copy2(output_path, backup_path)
        print("✓ Backup created")
        print()
    
    # Step 1: Scrape
    try:
        courses = scrape_all_courses(year, semester, campus, level)
        
        if not courses:
            print("❌ No courses found. Update cancelled.")
            return False
        
        print()
        print("🔄 Converting data format...")
        
        # Step 2: Convert
        bot_data = convert_api_data_to_bot_format(courses)
        
        if not bot_data.get('courses'):
            print("❌ No courses after conversion. Update cancelled.")
            return False
        
        # Step 3: Save
        print()
        print(f"💾 Saving to {output_file}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, indent=2, ensure_ascii=False)
        
        print()
        print("=" * 70)
        print("✓ UPDATE COMPLETE!")
        print("=" * 70)
        print(f"  Courses: {len(bot_data['courses'])}")
        print(f"  Core codes indexed: {len(bot_data['indexes']['by_core_code'])}")
        print(f"  Output file: {output_file}")
        print()
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠ Update cancelled by user")
        return False
    except Exception as e:
        print(f"\n\n❌ Error during update: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update course data for Rutgers Scheduler bot"
    )
    parser.add_argument(
        '--year', type=str,
        help='Year (e.g., 2026). Auto-detected if not provided.'
    )
    parser.add_argument(
        '--semester', choices=['spring', 'fall'],
        help='Semester. Auto-detected if not provided.'
    )
    parser.add_argument(
        '--campus', default='NB',
        help='Campus code (default: NB)'
    )
    parser.add_argument(
        '--level', default='UG',
        help='Level code (default: UG)'
    )
    parser.add_argument(
        '--output', default='rutgers_scheduler_data.json',
        help='Output file path (default: rutgers_scheduler_data.json)'
    )
    parser.add_argument(
        '--no-backup', action='store_true',
        help='Skip backing up existing data file'
    )
    
    args = parser.parse_args()
    
    success = update_bot_data(
        year=args.year,
        semester=args.semester,
        campus=args.campus,
        level=args.level,
        output_file=args.output,
        backup=not args.no_backup
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

