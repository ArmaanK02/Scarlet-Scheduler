"""
Data Converter: Transforms Rutgers SIS API data to app.py format
Converts course data from course_json_scraper.py output to rutgers_scheduler_data.json format
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime


def normalize_day(day_code: str) -> Optional[str]:
    """Convert day codes to full day names"""
    day_map = {
        'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday',
        'TH': 'Thursday', 'R': 'Thursday', 'F': 'Friday',
        'MONDAY': 'Monday', 'TUESDAY': 'Tuesday', 'WEDNESDAY': 'Wednesday',
        'THURSDAY': 'Thursday', 'FRIDAY': 'Friday',
    }
    if not day_code:
        return None
    d = day_code.strip().upper()
    if d in day_map:
        return day_map[d]
    for code, full in day_map.items():
        if d.startswith(code) or code.startswith(d):
            return full
    return None


def normalize_campus(campus: str) -> str:
    """Normalize campus names to abbreviations"""
    if not campus or not isinstance(campus, str):
        return ''
    c = campus.upper().strip()
    if 'BUSCH' in c or c == 'BUS':
        return 'BUS'
    if 'LIVINGSTON' in c or c == 'LIV':
        return 'LIV'
    if 'COLLEGE' in c or c == 'CAC':
        return 'CAC'
    if 'DOUGLASS' in c or 'COOK' in c or c == 'D/C':
        return 'D/C'
    if 'ONLINE' in c:
        return 'ONLINE'
    return c[:3] if len(c) >= 3 else c


def convert_time_format(time_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert time from API format to bot format.
    Returns (12h_format, 24h_format)
    """
    if not time_str:
        return None, None
    
    # Try to parse various time formats
    time_str = time_str.strip()
    
    # Already in 12h format (e.g., "10:20 AM")
    if 'AM' in time_str.upper() or 'PM' in time_str.upper():
        # Extract 24h format
        try:
            parts = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str.upper())
            if parts:
                h, m, period = int(parts.group(1)), int(parts.group(2)), parts.group(3)
                if period == 'PM' and h != 12:
                    h += 12
                elif period == 'AM' and h == 12:
                    h = 0
                time_24h = f"{h:02d}:{m:02d}"
                return time_str, time_24h
        except:
            pass
    
    # Try 24h format (e.g., "10:20")
    try:
        parts = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if parts:
            h, m = int(parts.group(1)), int(parts.group(2))
            if 0 <= h < 24 and 0 <= m < 60:
                # Convert to 12h
                period = 'AM' if h < 12 else 'PM'
                h_12 = h if h <= 12 else h - 12
                if h_12 == 0:
                    h_12 = 12
                time_12h = f"{h_12}:{m:02d} {period}"
                time_24h = f"{h:02d}:{m:02d}"
                return time_12h, time_24h
    except:
        pass
    
    return time_str, None


def convert_section(api_section: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a section from API format to bot format"""
    # Handle openStatus - can be string ('O'/'C') or boolean (True/False)
    open_status = api_section.get('openStatus', '')
    is_open = False
    if isinstance(open_status, bool):
        is_open = open_status
    elif isinstance(open_status, str):
        is_open = open_status.upper() == 'O'
    elif open_status:  # Truthy value
        is_open = True
    
    bot_section = {
        'section_number': api_section.get('number', ''),
        'index': str(api_section.get('index', '')),
        'is_open': is_open,
    }
    
    # Add section notes if available
    if api_section.get('sectionNotes'):
        bot_section['notes'] = api_section.get('sectionNotes')
    
    # Convert meeting times
    meetings = []
    api_meetings = api_section.get('meetingTimes', [])
    
    for mt in api_meetings:
        if not mt:
            continue
        
        day_code = mt.get('meetingDay', '')
        day_full = normalize_day(day_code)
        
        if not day_full:
            continue
        
        start_12h, start_24h = convert_time_format(mt.get('startTime', ''))
        end_12h, end_24h = convert_time_format(mt.get('endTime', ''))
        
        if not start_12h or not end_12h:
            continue
        
        meeting = {
            'day': day_full,
            'start_time': start_12h,
            'end_time': end_12h,
        }
        
        if start_24h:
            meeting['start_time_24h'] = start_24h
        if end_24h:
            meeting['end_time_24h'] = end_24h
        
        # Campus information
        campus = normalize_campus(mt.get('campusName', '') or mt.get('campusCode', ''))
        if campus:
            meeting['campus'] = campus
            meeting['campus_abbrev'] = campus
        
        # Building and room
        if mt.get('buildingCode'):
            meeting['building'] = mt.get('buildingCode')
        if mt.get('roomNumber'):
            meeting['room'] = mt.get('roomNumber')
        
        # Meeting mode (online, in-person, etc.)
        if mt.get('meetingModeDesc'):
            meeting['mode'] = mt.get('meetingModeDesc')
        
        meetings.append(meeting)
    
    bot_section['meetings'] = meetings
    return bot_section


def convert_course(api_course: Dict[str, Any]) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Convert a course from API format to bot format.
    Returns (course_key, bot_course_dict) or (None, None) if invalid
    """
    subject = str(api_course.get('subject', '')).strip()
    course_num = str(api_course.get('courseNumber', '')).strip()
    
    if not subject or not course_num:
        return None, None
    
    # Create course key in format "198:111"
    course_key = f"{subject.zfill(3)}:{course_num.zfill(3)}"
    
    # Convert core codes
    core_codes = []
    api_core_codes = api_course.get('coreCodes', [])
    if api_core_codes:
        for cc in api_core_codes:
            code = cc.get('code', '') if isinstance(cc, dict) else str(cc)
            if code:
                core_codes.append(code.strip().upper())
    
    # Build bot course structure
    bot_course = {
        'title': api_course.get('title', '') or api_course.get('expandedTitle', ''),
        'credits': float(api_course.get('credits', 0)) if api_course.get('credits') else 0,
        'prerequisites': api_course.get('preReqNotes', '') or '',
        'core_codes': core_codes,
        'sections': [],
    }
    
    # Add description if available
    if api_course.get('courseDescription'):
        bot_course['description'] = api_course.get('courseDescription')
    
    # Convert sections
    api_sections = api_course.get('sections', [])
    for api_sec in api_sections:
        if not api_sec:
            continue
        bot_section = convert_section(api_sec)
        if bot_section.get('meetings'):  # Only add sections with valid meetings
            bot_course['sections'].append(bot_section)
    
    # If no sections, still add the course (might be async/online)
    if not bot_course['sections'] and api_sections:
        # Add sections even without meetings
        for api_sec in api_sections:
            bot_section = convert_section(api_sec)
            bot_course['sections'].append(bot_section)
    
    return course_key, bot_course


def convert_api_data_to_bot_format(api_courses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert list of API courses to bot's expected format.
    Returns: {"courses": {...}, "indexes": {"by_core_code": {...}}}
    """
    bot_data = {
        "courses": {},
        "indexes": {"by_core_code": {}}
    }
    
    converted_count = 0
    skipped_count = 0
    
    for api_course in api_courses:
        course_key, bot_course = convert_course(api_course)
        
        if not course_key or not bot_course:
            skipped_count += 1
            continue
        
        # Add to courses
        bot_data["courses"][course_key] = bot_course
        converted_count += 1
        
        # Index by core codes
        for core_code in bot_course.get('core_codes', []):
            if core_code not in bot_data["indexes"]["by_core_code"]:
                bot_data["indexes"]["by_core_code"][core_code] = []
            if course_key not in bot_data["indexes"]["by_core_code"][core_code]:
                bot_data["indexes"]["by_core_code"][core_code].append(course_key)
    
    print(f"✓ Converted {converted_count} courses")
    if skipped_count > 0:
        print(f"⚠ Skipped {skipped_count} invalid courses")
    
    return bot_data


def convert_json_file(input_path: str, output_path: str = None) -> bool:
    """
    Convert a JSON file from API format to bot format.
    
    Args:
        input_path: Path to input JSON file (from scraper)
        output_path: Path to output JSON file (default: rutgers_scheduler_data.json)
    
    Returns:
        True if successful, False otherwise
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ Input file not found: {input_path}")
        return False
    
    if output_path is None:
        output_path = "rutgers_scheduler_data.json"
    
    output_file = Path(output_path)
    
    try:
        print(f"📖 Reading {input_path}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            api_data = json.load(f)
        
        if not isinstance(api_data, list):
            print(f"❌ Expected list of courses, got {type(api_data)}")
            return False
        
        print(f"📊 Found {len(api_data)} courses in API format")
        print("🔄 Converting to bot format...")
        
        bot_data = convert_api_data_to_bot_format(api_data)
        
        print(f"💾 Saving to {output_path}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(bot_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully converted and saved {len(bot_data['courses'])} courses")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_converter.py <input_json_file> [output_json_file]")
        print("\nExample:")
        print("  python data_converter.py rutgers_courses_Spring2026_NB_20250101_120000.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = convert_json_file(input_file, output_file)
    sys.exit(0 if success else 1)

