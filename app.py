#!/usr/bin/env python3
"""
Rutgers Course Scheduler - Smart Edition
=========================================
Features:
- PREREQUISITE CHECKING - won't schedule courses with unmet prereqs
- SAS CORE SUPPORT - can fill core requirements intelligently
- LLM-POWERED - handles vague prompts
- VISUAL CALENDAR - shows all classes correctly
"""

import json
import os
import re
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path

# ============================================
# Load .env file
# ============================================

def load_env():
    for env_file in [Path(".env"), Path(".env.txt")]:
        if env_file.exists():
            try:
                content = env_file.read_text(encoding='utf-8')
                if content.startswith('\ufeff'):
                    content = content[1:]
                for line in content.splitlines():
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        key, val = line.split("=", 1)
                        key = key.strip().replace('\x00', '')
                        val = val.strip().strip('"').strip("'").replace('\x00', '')
                        if key and val:
                            os.environ[key] = val
                return True
            except:
                pass
    return False

load_env()

# ============================================
# HUGGINGFACE CLIENT FOR LLM
# ============================================

HF_CLIENT = None

try:
    from huggingface_hub import InferenceClient
    token = os.environ.get("HF_TOKEN")
    if token:
        HF_CLIENT = InferenceClient(token=token)
        print("✓ LLM client initialized")
    else:
        print("⚠ No HF_TOKEN - LLM features disabled")
except ImportError:
    print("⚠ huggingface_hub not installed")

MODEL_ID = "deepseek-ai/DeepSeek-R1-0528"

# ============================================
# CONFIG
# ============================================

DATABASE_PATHS = [
    "rutgers_scheduler_data.json",
    "rutgers_scheduler_data (1).json",
]

def find_database():
    for path in DATABASE_PATHS:
        if Path(path).exists():
            return path
    return DATABASE_PATHS[0]

DATABASE_PATH = find_database()

MIN_CREDITS = 12
TARGET_CREDITS = 15
MAX_CREDITS = 18

# ============================================
# SAS CORE REQUIREMENTS
# ============================================

SAS_CORE_CODES = {
    'AHo': 'Arts & Humanities - Arts',
    'AHp': 'Arts & Humanities - Literature', 
    'AHq': 'Arts & Humanities - Philosophy',
    'AHr': 'Arts & Humanities - Religion',
    'CCD': 'Contemporary Challenges - Diversity',
    'CCO': 'Contemporary Challenges - Our Common Future',
    'HST': 'Historical Analysis',
    'ITR': 'Information Technology',
    'NS': 'Natural Sciences',
    'QQ': 'Quantitative & Formal Reasoning - Math',
    'QR': 'Quantitative & Formal Reasoning - Reasoning',
    'SCL': 'Social Analysis',
    'WCd': 'Writing & Communication - Writing',
    'WCr': 'Writing & Communication - Revision',
}

# Freshman-friendly core courses (usually no prereqs)
FRESHMAN_CORE_SUGGESTIONS = {
    'QQ': ['640:025', '640:026', '640:103', '640:111', '640:112'],  # Basic math
    'QR': ['198:110', '940:108', '300:105'],  # Reasoning courses
    'NS': ['119:101', '119:102', '160:101', '160:103', '750:101'],  # Intro sciences
    'SCL': ['920:101', '790:101', '070:101', '220:102'],  # Social sciences
    'HST': ['510:101', '510:102', '508:201'],  # History
    'WCd': ['355:101', '355:201'],  # Writing
    'AHo': ['081:101', '700:101', '206:101'],  # Arts
    'AHp': ['350:101', '350:102'],  # Literature
    'CCD': ['014:101', '988:101', '595:101'],  # Diversity
    'CCO': ['374:101', '832:101'],  # Contemporary
    'ITR': ['547:200', '547:201'],  # IT
}

# ============================================
# SUBJECT CODES
# ============================================

SUBJECT_CODES = {
    '198': 'Computer Science', '640': 'Mathematics', '750': 'Physics',
    '160': 'Chemistry', '119': 'Biology', '220': 'Economics',
    '830': 'Psychology', '920': 'Sociology', '790': 'Political Science',
    '730': 'Philosophy', '350': 'English', '510': 'History',
    '700': 'Music', '010': 'Accounting', '960': 'Statistics',
    '192': 'Communication', '440': 'Engineering', '650': 'Mechanical Engineering',
    '155': 'Chemical Engineering', '180': 'Civil Engineering',
    '540': 'Industrial Engineering', '332': 'Electrical Engineering',
    '547': 'Information Technology', '202': 'Criminal Justice',
    '567': 'Journalism', '377': 'Exercise Science', '374': 'Environmental Science',
    '832': 'Public Health', '833': 'Public Policy', '910': 'Social Work',
    '533': 'Human Resources', '620': 'Business/Management',
    '081': 'Visual Arts', '966': 'Theater', '211': 'Film', '206': 'Dance',
    '070': 'Anthropology', '067': 'Animal Science', '725': 'Pharmacy',
    '300': 'Education', '450': 'Geography', '460': 'Geology', '840': 'Religion',
    '575': 'Labor Studies', '988': "Women's Studies", '014': 'Africana Studies',
}

# ============================================
# CAMPUS & TIME UTILITIES
# ============================================

CAMPUS_COLORS = {
    'BUS': '#cc0033', 'LIV': '#3498db', 'CAC': '#27ae60',
    'D/C': '#9b59b6', 'ONLINE': '#7f8c8d', '': '#95a5a6'
}

CAMPUS_NAMES = {
    'BUS': 'Busch', 'LIV': 'Livingston', 'CAC': 'College Ave',
    'D/C': 'Cook/Douglass', 'ONLINE': 'Online', '': 'TBA'
}

DAY_MAP = {
    'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday',
    'TH': 'Thursday', 'R': 'Thursday', 'F': 'Friday',
    'MONDAY': 'Monday', 'TUESDAY': 'Tuesday', 'WEDNESDAY': 'Wednesday',
    'THURSDAY': 'Thursday', 'FRIDAY': 'Friday',
}

def normalize_day(day_code: str) -> Optional[str]:
    if not day_code:
        return None
    d = day_code.strip().upper()
    if d in DAY_MAP:
        return DAY_MAP[d]
    for code, full in DAY_MAP.items():
        if d.startswith(code) or code.startswith(d):
            return full
    return None

def normalize_campus(campus) -> str:
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

def time_to_minutes(t) -> Optional[int]:
    if not t:
        return None
    if not isinstance(t, str):
        try:
            t = str(t)
        except:
            return None
    t = t.strip()
    if not t:
        return None
    try:
        t_upper = t.upper()
        match = re.match(r'(\d{1,2}):(\d{2})(?::\d{2})?\s*(AM|PM)?', t_upper)
        if match:
            h, m, period = int(match.group(1)), int(match.group(2)), match.group(3)
            if period == 'PM' and h != 12:
                h += 12
            elif period == 'AM' and h == 12:
                h = 0
            elif not period and h < 8:
                h += 12
            if 0 <= h < 24 and 0 <= m < 60:
                return h * 60 + m
    except:
        pass
    return None

def minutes_to_time(mins: int) -> str:
    h, m = mins // 60, mins % 60
    period = 'AM' if h < 12 else 'PM'
    if h > 12:
        h -= 12
    elif h == 0:
        h = 12
    return f"{h}:{m:02d} {period}"


# ============================================
# VISUAL SCHEDULE GENERATOR
# ============================================

def generate_visual_schedule(schedule: List[Dict], scheduler, title: str = "Your Schedule") -> str:
    """Generate HTML visual calendar"""
    
    if not schedule:
        return """<div style='padding:60px; text-align:center; color:#666; background:#f8f9fa; 
                   border-radius:16px; border: 2px dashed #dee2e6;'>
                   <div style='font-size:56px; margin-bottom:20px;'>📅</div>
                   <div style='font-size:22px; font-weight:600;'>No Schedule Yet</div>
                </div>"""
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    meetings_by_day = {d: [] for d in days}
    all_times = []
    
    for sec in schedule:
        if not sec:
            continue
        course_key = sec.get('course_key', '')
        course = scheduler.get_course(course_key) if scheduler else None
        course_name = course.get('title', course_key) if course else course_key
        
        for m in sec.get('meetings', []):
            if not m:
                continue
            
            raw_day = m.get('day', '')
            day_full = normalize_day(raw_day)
            
            if not day_full or day_full not in days:
                continue
            
            start = time_to_minutes(m.get('start_time_24h') or m.get('start_time'))
            end = time_to_minutes(m.get('end_time_24h') or m.get('end_time'))
            
            if start and end and start < end:
                all_times.extend([start, end])
                campus = normalize_campus(m.get('campus_abbrev') or m.get('campus'))
                meetings_by_day[day_full].append({
                    'course': course_key,
                    'name': course_name,
                    'start': start,
                    'end': end,
                    'start_str': m.get('start_time', ''),
                    'end_str': m.get('end_time', ''),
                    'campus': campus,
                    'is_open': sec.get('is_open', True)
                })
    
    if not all_times:
        return """<div style='padding:40px; text-align:center; color:#666;'>
                   <div style='font-size:48px;'>📅</div>
                   <div>No class meetings found</div></div>"""
    
    # Calculate time range
    min_time = min(all_times)
    max_time = max(all_times)
    min_time = (min_time // 60) * 60
    max_time = ((max_time // 60) + 1) * 60
    min_time = max(min_time - 60, 7 * 60)
    max_time = min(max_time + 60, 23 * 60)
    
    total_meetings = sum(len(m) for m in meetings_by_day.values())
    
    # Use absolute positioning
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: white; padding: 24px; border-radius: 16px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
        <h2 style="text-align: center; color: #cc0033; margin: 0 0 8px 0; font-size: 26px;">
            📅 {title}
        </h2>
        <p style="text-align: center; color: #666; margin: 0 0 20px 0; font-size: 14px;">
            {total_meetings} class meetings | {sum(1 for d in days if meetings_by_day[d])} days
        </p>
        
        <div style="display: grid; grid-template-columns: 70px repeat(5, 1fr); background: #f0f0f0; 
                    border-radius: 12px; overflow: hidden; gap: 1px;">
            
            <div style="background: #cc0033; color: white; padding: 12px 6px; text-align: center; 
                        font-weight: 700; font-size: 12px;">Time</div>
    """
    
    for day in days:
        html += f'''<div style="background: #cc0033; color: white; padding: 12px 6px; 
                    text-align: center; font-weight: 700; font-size: 13px;">{day[:3]}</div>'''
    
    pixels_per_minute = 1.5
    total_height = int((max_time - min_time) * pixels_per_minute)
    
    # Time labels column
    html += f'''<div style="background: #f8f8f8; position: relative; height: {total_height}px;">'''
    for hour in range(min_time // 60, max_time // 60 + 1):
        top = int((hour * 60 - min_time) * pixels_per_minute)
        time_str = minutes_to_time(hour * 60)
        html += f'''<div style="position: absolute; top: {top}px; right: 4px; font-size: 11px; 
                    color: #666; transform: translateY(-50%);">{time_str}</div>'''
    html += '</div>'
    
    # Day columns with meetings
    for day in days:
        html += f'''<div style="background: white; position: relative; height: {total_height}px; 
                    border-left: 1px solid #e0e0e0;">'''
        
        for hour in range(min_time // 60, max_time // 60 + 1):
            top = int((hour * 60 - min_time) * pixels_per_minute)
            html += f'''<div style="position: absolute; top: {top}px; left: 0; right: 0; 
                        border-top: 1px solid #f0f0f0;"></div>'''
        
        for m in meetings_by_day[day]:
            top = int((m['start'] - min_time) * pixels_per_minute)
            height = int((m['end'] - m['start']) * pixels_per_minute)
            height = max(height, 50)
            
            color = CAMPUS_COLORS.get(m['campus'], '#6c757d')
            border = "solid" if m['is_open'] else "dashed"
            display_name = m['name'][:20] + '..' if len(m['name']) > 20 else m['name']
            
            html += f"""
            <div style="position: absolute; top: {top}px; left: 3px; right: 3px;
                height: {height}px; background: {color};
                border-radius: 6px; padding: 4px 6px; color: white;
                font-size: 10px; overflow: hidden;
                border: 2px {border} rgba(255,255,255,0.3);
                box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
                <div style="font-weight: 700; font-size: 11px;">{display_name}</div>
                <div style="font-size: 9px; opacity: 0.9;">{m['course']}</div>
                <div style="font-size: 9px; opacity: 0.85;">{m['start_str']}-{m['end_str']}</div>
                <div style="font-size: 9px; opacity: 0.8;">{CAMPUS_NAMES.get(m['campus'], '')}</div>
            </div>"""
        
        html += '</div>'
    
    # Legend
    html += """</div>
        <div style="margin-top: 20px; display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; 
                    padding: 14px; background: #f8f9fa; border-radius: 10px;">"""
    
    for campus, color in [('BUS', '#cc0033'), ('LIV', '#3498db'), ('CAC', '#27ae60'), ('D/C', '#9b59b6')]:
        html += f'''<div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 14px; height: 14px; background: {color}; border-radius: 3px;"></div>
                    <span style="font-size: 12px; color: #555;">{CAMPUS_NAMES[campus]}</span></div>'''
    
    html += "</div></div>"
    return html


# ============================================
# SCHEDULER CLASS WITH PREREQ CHECKING
# ============================================

class RutgersScheduler:
    def __init__(self, db_path: str = None):
        self.data = {"courses": {}, "indexes": {"by_core_code": {}}}
        self.filler_courses = []
        self.no_prereq_courses = []  # Courses safe for freshmen
        
        db_path = db_path or DATABASE_PATH
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self._build_course_lists()
            print(f"✓ Loaded {len(self.data['courses'])} courses")
            print(f"✓ {len(self.no_prereq_courses)} courses with no prerequisites")
        except Exception as e:
            print(f"⚠ Error loading database: {e}")
    
    def _build_course_lists(self):
        """Build lists of filler courses, prioritizing those without prereqs"""
        all_candidates = []
        no_prereq_candidates = []
        
        for key, course in self.data['courses'].items():
            sections = course.get('sections', [])
            open_ct = sum(1 for s in sections if s and s.get('is_open'))
            try:
                credits = float(course.get('credits', 0))
            except:
                credits = 0
            
            if open_ct < 1 or credits < 1 or credits > 4:
                continue
            
            has_prereq = bool(course.get('prerequisites', '').strip())
            core_codes = course.get('core_codes', [])
            
            # Base score
            score = open_ct * 2
            if core_codes:
                score += len(core_codes) * 30  # Core courses are valuable
            if 3 <= credits <= 4:
                score += 20
            
            # Course number - prefer intro courses
            try:
                course_num = int(key.split(':')[1])
                if course_num < 200:
                    score += 50  # Intro course bonus
                elif course_num < 300:
                    score += 20
            except:
                pass
            
            candidate = {
                'key': key,
                'title': course.get('title', ''),
                'credits': credits,
                'open_sections': open_ct,
                'core_codes': core_codes,
                'has_prereq': has_prereq,
                'score': score
            }
            
            all_candidates.append(candidate)
            
            # No-prereq courses get extra priority
            if not has_prereq:
                candidate_copy = dict(candidate)
                candidate_copy['score'] += 100  # Big bonus for no prereq
                no_prereq_candidates.append(candidate_copy)
        
        # Sort by score
        all_candidates.sort(key=lambda x: -x['score'])
        no_prereq_candidates.sort(key=lambda x: -x['score'])
        
        self.filler_courses = all_candidates[:600]
        self.no_prereq_courses = no_prereq_candidates[:400]
        
        print(f"✓ Indexed {len(self.filler_courses)} filler courses")
    
    def has_prerequisites(self, key: str) -> bool:
        """Check if a course has prerequisites"""
        course = self.get_course(key)
        if not course:
            return False
        prereq = course.get('prerequisites', '')
        return bool(prereq and prereq.strip())
    
    def get_prerequisites(self, key: str) -> str:
        """Get prerequisite text for a course"""
        course = self.get_course(key)
        if not course:
            return ''
        return course.get('prerequisites', '') or ''
    
    def check_prereq_conflict(self, new_key: str, scheduled_keys: Set[str]) -> bool:
        """
        Check if adding this course would create a prerequisite conflict.
        Returns True if there IS a conflict (course should not be added).
        """
        prereq_text = self.get_prerequisites(new_key)
        if not prereq_text:
            return False  # No prereqs, no conflict
        
        # Check if any scheduled course is a prereq for this course
        # This would mean taking prereq and course at same time = conflict
        for scheduled_key in scheduled_keys:
            # Normalize the key format for comparison
            # Prereqs are stored as "01:198:111" format
            short_key = scheduled_key  # e.g., "198:111"
            long_key = f"01:{scheduled_key}"  # e.g., "01:198:111"
            
            if short_key in prereq_text or long_key in prereq_text:
                return True  # This course requires a course we're taking = conflict
        
        return False
    
    def get_course(self, key: str) -> Optional[Dict]:
        if not key:
            return None
        key = str(key).strip()
        course = self.data['courses'].get(key)
        if course:
            return course
        parts = key.split(':')
        if len(parts) == 2:
            padded = f"{parts[0].zfill(3)}:{parts[1].zfill(3)}"
            return self.data['courses'].get(padded)
        return None
    
    def get_courses_by_core(self, core: str) -> List[str]:
        """Get courses that satisfy a core requirement, prioritizing no-prereq courses"""
        all_courses = self.data.get('indexes', {}).get('by_core_code', {}).get(core.upper(), [])
        
        # Score and sort courses
        scored = []
        for key in all_courses:
            course = self.get_course(key)
            if not course:
                continue
            
            open_ct = sum(1 for s in course.get('sections', []) if s and s.get('is_open'))
            if open_ct == 0:
                continue
            
            has_prereq = bool(course.get('prerequisites', '').strip())
            
            score = open_ct * 2
            if not has_prereq:
                score += 100  # Big bonus for no prereqs
            
            try:
                course_num = int(key.split(':')[1])
                if course_num < 200:
                    score += 50
            except:
                pass
            
            scored.append((key, score, has_prereq))
        
        scored.sort(key=lambda x: -x[1])
        return [x[0] for x in scored]
    
    def is_math_only_prereq(self, key: str) -> bool:
        """Check if course only has math prerequisites (typically co-requisites for freshmen)"""
        prereq = self.get_prerequisites(key).lower()
        if not prereq:
            return False
        
        # Check if prereq only mentions math courses (640:xxx)
        # These are typically taken concurrently by freshmen
        math_pattern = r'640:\d{3}'
        other_pattern = r'(?<!6)(?<!4)(?<!0)\d{3}:\d{3}'  # Any non-640 course
        
        has_math = bool(re.search(math_pattern, prereq))
        has_other = bool(re.search(r'(?:198|750|160|119|220|830):\d{3}', prereq))
        
        return has_math and not has_other
    
    def get_courses_by_subject(self, subject_code: str, freshman_safe: bool = True) -> List[str]:
        """Get intro courses for a subject, with smart freshman filtering"""
        candidates = []
        
        # Known intro courses that freshmen can take (even with math co-reqs)
        FRESHMAN_INTRO_COURSES = {
            '198': ['198:111', '198:110'],  # Intro CS
            '640': ['640:103', '640:111', '640:112', '640:115', '640:151'],  # Math
            '750': ['750:101', '750:103', '750:115', '750:116'],  # Physics
            '160': ['160:101', '160:103', '160:161'],  # Chemistry
            '119': ['119:101', '119:102', '119:115', '119:116'],  # Biology
            '220': ['220:102', '220:103'],  # Economics
            '830': ['830:101'],  # Psychology
            '920': ['920:101'],  # Sociology
            '790': ['790:101', '790:104'],  # Political Science
            '202': ['202:201'],  # Criminal Justice
        }
        
        safe_intros = set(FRESHMAN_INTRO_COURSES.get(subject_code, []))
        
        for key in self.data['courses'].keys():
            if not key.startswith(f"{subject_code}:"):
                continue
            
            course = self.data['courses'][key]
            open_ct = sum(1 for s in course.get('sections', []) if s and s.get('is_open'))
            if open_ct == 0:
                continue
            
            has_prereq = bool(course.get('prerequisites', '').strip())
            math_only_prereq = self.is_math_only_prereq(key)
            is_known_intro = key in safe_intros
            
            # In freshman_safe mode:
            # - Always allow known intro courses
            # - Allow courses with only math prereqs (co-requisites)
            # - Skip courses with other prereqs
            if freshman_safe and has_prereq:
                if not (is_known_intro or math_only_prereq):
                    continue
            
            course_num = key.split(':')[1] if ':' in key else ''
            score = open_ct * 2
            
            # Scoring
            if is_known_intro:
                score += 200  # Strong preference for known intro courses
            if course_num.startswith('1'):
                score += 100
            elif course_num.startswith('2'):
                score += 50
            if not has_prereq:
                score += 80
            elif math_only_prereq:
                score += 40  # Math co-reqs are okay
            
            candidates.append((key, score))
        
        candidates.sort(key=lambda x: -x[1])
        return [c[0] for c in candidates[:10]]
    
    def get_sections(self, key: str, open_only=True, exclude_days=None,
                     start_after=None, end_before=None) -> List[Dict]:
        course = self.get_course(key)
        if not course:
            return []
        
        exclude = set(d.upper() for d in (exclude_days or []))
        start_mins = time_to_minutes(start_after) if start_after else None
        end_mins = time_to_minutes(end_before) if end_before else None
        
        results = []
        for sec in course.get('sections', []):
            if not sec:
                continue
            if open_only and not sec.get('is_open'):
                continue
            
            sec_copy = dict(sec)
            sec_copy['course_key'] = key
            
            skip = False
            for m in sec.get('meetings', []):
                if not m:
                    continue
                day = (m.get('day') or '').upper()
                if day in exclude or (day == 'TH' and 'TH' in exclude) or (day == 'F' and 'F' in exclude):
                    skip = True
                    break
                if start_mins:
                    s = time_to_minutes(m.get('start_time_24h') or m.get('start_time'))
                    if s and s < start_mins:
                        skip = True
                        break
                if end_mins:
                    e = time_to_minutes(m.get('end_time_24h') or m.get('end_time'))
                    if e and e > end_mins:
                        skip = True
                        break
            
            if not skip:
                results.append(sec_copy)
        
        return results
    
    def check_conflict(self, sec1: Dict, sec2: Dict) -> bool:
        for m1 in sec1.get('meetings', []):
            if not m1:
                continue
            for m2 in sec2.get('meetings', []):
                if not m2:
                    continue
                
                d1 = normalize_day(m1.get('day', ''))
                d2 = normalize_day(m2.get('day', ''))
                
                if not d1 or not d2 or d1 != d2:
                    continue
                
                s1 = time_to_minutes(m1.get('start_time_24h') or m1.get('start_time'))
                e1 = time_to_minutes(m1.get('end_time_24h') or m1.get('end_time'))
                s2 = time_to_minutes(m2.get('start_time_24h') or m2.get('start_time'))
                e2 = time_to_minutes(m2.get('end_time_24h') or m2.get('end_time'))
                
                if s1 is None or e1 is None or s2 is None or e2 is None:
                    continue
                
                if s1 < e2 and s2 < e1:
                    return True
        
        return False
    
    def can_add_section(self, section: Dict, schedule: List[Dict]) -> bool:
        for existing in schedule:
            if self.check_conflict(section, existing):
                return False
        return True
    
    def build_schedule(self, course_keys: List[str], prefs: Dict = None,
                       include_closed: bool = False, target_credits: float = TARGET_CREDITS,
                       freshman_safe: bool = True) -> Dict:
        """
        Build a schedule with PREREQUISITE CHECKING.
        freshman_safe=True means only add courses without prerequisites during auto-fill.
        """
        prefs = prefs or {}
        exclude_days = prefs.get('exclude_days', [])
        
        result = {
            'schedule': [], 'failed': [], 'warnings': [],
            'total_credits': 0, 'auto_added': [], 'prereq_issues': []
        }
        
        scheduled_keys = set()
        
        # Schedule requested courses
        for key in course_keys:
            if key in scheduled_keys:
                continue
            
            # Check for prerequisite issues with already-scheduled courses
            if self.check_prereq_conflict(key, scheduled_keys):
                result['prereq_issues'].append({
                    'course': key,
                    'reason': f"Cannot take {key} - requires a course you're scheduling simultaneously"
                })
                result['failed'].append(key)
                continue
            
            sections = self.get_sections(key, open_only=not include_closed,
                                        exclude_days=exclude_days,
                                        start_after=prefs.get('start_after'),
                                        end_before=prefs.get('end_before'))
            
            added = False
            for sec in sections:
                if self.can_add_section(sec, result['schedule']):
                    result['schedule'].append(sec)
                    scheduled_keys.add(key)
                    added = True
                    break
            
            if not added and key not in scheduled_keys:
                result['failed'].append(key)
        
        # Calculate credits
        def calc_credits(sched):
            total = 0
            for sec in sched:
                c = self.get_course(sec.get('course_key', ''))
                if c:
                    try:
                        total += float(c.get('credits', 0))
                    except:
                        pass
            return total
        
        result['total_credits'] = calc_credits(result['schedule'])
        
        # Auto-fill with NO-PREREQ courses only
        filler_list = self.no_prereq_courses if freshman_safe else self.filler_courses
        
        attempts = 0
        while result['total_credits'] < target_credits and attempts < 80:
            attempts += 1
            added = False
            
            for filler in filler_list:
                if filler['key'] in scheduled_keys:
                    continue
                if result['total_credits'] + filler['credits'] > MAX_CREDITS:
                    continue
                
                # Skip if has prereq and we're in freshman_safe mode
                if freshman_safe and filler['has_prereq']:
                    continue
                
                # Check prereq conflicts
                if self.check_prereq_conflict(filler['key'], scheduled_keys):
                    continue
                
                sections = self.get_sections(filler['key'], open_only=True,
                                            exclude_days=exclude_days,
                                            start_after=prefs.get('start_after'),
                                            end_before=prefs.get('end_before'))
                
                for sec in sections:
                    if self.can_add_section(sec, result['schedule']):
                        result['schedule'].append(sec)
                        scheduled_keys.add(filler['key'])
                        result['auto_added'].append(filler['key'])
                        result['total_credits'] += filler['credits']
                        added = True
                        break
                
                if added:
                    break
            
            if not added:
                break
        
        return result
    
    def build_core_schedule(self, core_codes: List[str], prefs: Dict = None,
                           target_credits: float = TARGET_CREDITS) -> Dict:
        """Build a schedule focusing on specific core requirements"""
        prefs = prefs or {}
        courses_to_schedule = []
        
        for code in core_codes:
            code = code.upper()
            candidates = self.get_courses_by_core(code)
            if candidates:
                # Take the best (highest scored, no-prereq preferred)
                courses_to_schedule.append(candidates[0])
        
        return self.build_schedule(courses_to_schedule, prefs, False, target_credits, True)
    
    def format_schedule(self, build_result: Dict) -> str:
        schedule = build_result.get('schedule', [])
        auto_added = set(build_result.get('auto_added', []))
        total_credits = build_result.get('total_credits', 0)
        prereq_issues = build_result.get('prereq_issues', [])
        
        if not schedule:
            return "# ❌ Could Not Build Schedule\n\nNo valid schedule found."
        
        lines = [f"# 📅 Your Schedule ({total_credits:.0f} credits)\n"]
        
        # Warning about prereq issues
        if prereq_issues:
            lines.append("## ⚠️ Prerequisite Issues\n")
            for issue in prereq_issues:
                lines.append(f"- **{issue['course']}**: {issue['reason']}")
            lines.append("")
        
        indexes = []
        
        # User courses
        requested = [s for s in schedule if s.get('course_key') not in auto_added]
        if requested:
            lines.append("## 📚 Your Courses\n")
            for sec in requested:
                self._format_section(sec, lines, indexes)
        
        # Auto-added
        added = [s for s in schedule if s.get('course_key') in auto_added]
        if added:
            lines.append("\n## ✨ Auto-Added Courses (No Prerequisites)\n")
            for sec in added:
                self._format_section(sec, lines, indexes)
        
        if indexes:
            lines.append(f"\n---\n## 🎯 Registration Indexes\n```\n{', '.join(indexes)}\n```")
        
        return "\n".join(lines)
    
    def _format_section(self, sec: Dict, lines: List[str], indexes: List[str]):
        key = sec.get('course_key', '')
        course = self.get_course(key)
        if not course:
            return
        
        title = course.get('title', 'Unknown')
        credits = course.get('credits', '?')
        idx = sec.get('index', '')
        if idx:
            indexes.append(str(idx))
        
        status = "✅ OPEN" if sec.get('is_open') else "⚠️ CLOSED"
        prereq = "📋 Has Prerequisites" if course.get('prerequisites') else "✓ No Prerequisites"
        
        lines.append(f"### {title}")
        lines.append(f"**{key}** | {credits} credits | Index: `{idx}` {status}")
        lines.append(f"{prereq}")
        
        if course.get('core_codes'):
            lines.append(f"**Core:** {', '.join(course['core_codes'])}")
        
        for m in sec.get('meetings', []):
            if m and m.get('day'):
                campus = m.get('campus') or m.get('campus_abbrev', 'TBA')
                lines.append(f"- {m.get('day')}: {m.get('start_time')} - {m.get('end_time')} @ {campus}")
        lines.append("")
    
    def format_course_info(self, key: str) -> str:
        course = self.get_course(key)
        if not course:
            return f"❌ Course `{key}` not found."
        
        lines = [f"# {course.get('title', 'Unknown')}\n"]
        lines.append(f"**Code:** {key} | **Credits:** {course.get('credits', '?')}")
        
        if course.get('core_codes'):
            lines.append(f"**Core:** {', '.join(course['core_codes'])}")
        
        prereq = course.get('prerequisites', '')
        if prereq:
            lines.append(f"\n**⚠️ Prerequisites:** {prereq}")
        else:
            lines.append("\n**✓ Prerequisites:** None - safe for freshmen!")
        
        sections = course.get('sections', [])
        open_ct = sum(1 for s in sections if s and s.get('is_open'))
        lines.append(f"\n## Sections ({open_ct} open)\n")
        
        for sec in sections[:5]:
            if sec and sec.get('is_open'):
                lines.append(f"**Section {sec.get('section_number', '?')}** | Index: `{sec.get('index')}`")
                for m in sec.get('meetings', []):
                    if m:
                        lines.append(f"- {m.get('day')}: {m.get('start_time')}-{m.get('end_time')}")
                lines.append("")
        
        return "\n".join(lines)


# ============================================
# LLM PROCESSING
# ============================================

def call_llm(prompt: str, system: str = None) -> Optional[str]:
    if not HF_CLIENT:
        return None
    
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = HF_CLIENT.chat_completion(
            model=MODEL_ID,
            messages=messages,
            max_tokens=1500,
            temperature=0.7,
        )
        
        if response and response.choices:
            content = response.choices[0].message.content
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            return content.strip()
    except Exception as e:
        print(f"LLM error: {e}")
    
    return None


def detect_subject(text: str) -> Optional[str]:
    if not text:
        return None
    
    text_lower = ' ' + text.lower() + ' '
    
    mappings = [
        (r'\bcomputer science\b', '198'), (r'\bcomp sci\b', '198'), (r'\bcompsci\b', '198'),
        (r'\beconomics\b', '220'), (r'\becon\b', '220'),
        (r'\bmechanical engineering\b', '650'), (r'\bchemical engineering\b', '155'),
        (r'\bcivil engineering\b', '180'), (r'\belectrical engineering\b', '332'),
        (r'\bpolitical science\b', '790'), (r'\bpoli sci\b', '790'),
        (r'\bcriminal justice\b', '202'), (r'\bcriminology\b', '202'),
        (r'\bpublic health\b', '832'), (r'\bpublic policy\b', '833'),
        (r'\bexercise science\b', '377'), (r'\benvironmental science\b', '374'),
        (r'\bjournalism\b', '567'), (r'\bmedia studies\b', '567'),
        (r'\binformation technology\b', '547'),
        (r'\bsocial work\b', '910'), (r'\bhuman resources\b', '533'),
        (r'\bbusiness\b', '620'), (r'\bmanagement\b', '620'),
        (r'\btheater\b', '966'), (r'\btheatre\b', '966'),
        (r'\bfilm\b', '211'), (r'\bdance\b', '206'), (r'\bmusic\b', '700'),
        (r'\bphilosophy\b', '730'), (r'\breligion\b', '840'),
        (r'\banthropology\b', '070'), (r'\beducation\b', '300'),
        (r'\bgeography\b', '450'), (r'\bgeology\b', '460'),
        (r'\bphysics\b', '750'), (r'\bchemistry\b', '160'),
        (r'\bbiology\b', '119'), (r'\bpsychology\b', '830'),
        (r'\bmathematics\b', '640'), (r'\bsociology\b', '920'),
        (r'\bstatistics\b', '960'), (r'\bhistory\b', '510'),
        (r'\benglish\b', '350'), (r'\baccounting\b', '010'),
        (r'\bpsych\b', '830'), (r'\bbio\b', '119'), (r'\bchem\b', '160'),
        (r'\bphys\b', '750'), (r'\bmath\b', '640'), (r'\bstats\b', '960'),
        (r'\bcs\b', '198'), (r'\bit\b', '547'), (r'\bcj\b', '202'),
    ]
    
    for pattern, code in mappings:
        if re.search(pattern, text_lower):
            return code
    
    return None


def extract_prefs(text: str) -> Dict:
    prefs = {}
    t = text.lower()
    
    if any(x in t for x in ['no friday', 'fridays off']):
        prefs['exclude_days'] = prefs.get('exclude_days', []) + ['F']
    if any(x in t for x in ['no monday', 'mondays off']):
        prefs['exclude_days'] = prefs.get('exclude_days', []) + ['M']
    if any(x in t for x in ['no morning', 'late start', 'after 10']):
        prefs['start_after'] = '10:00'
    if 'after 11' in t:
        prefs['start_after'] = '11:00'
    if any(x in t for x in ['no evening', 'before 6']):
        prefs['end_before'] = '18:00'
    
    return prefs


def parse_courses(text: str, scheduler) -> List[str]:
    found = []
    seen = set()
    
    for match in re.finditer(r'\b(\d{2,3}):(\d{3})\b', text):
        key = f"{match.group(1).zfill(3)}:{match.group(2)}"
        if key not in seen and scheduler.get_course(key):
            found.append(key)
            seen.add(key)
    
    patterns = [
        (r'\b(?:cs|comp\s*sci)\s*(\d{3})\b', '198'),
        (r'\bmath\s*(\d{3})\b', '640'),
        (r'\bphysics?\s*(\d{3})\b', '750'),
        (r'\bchem(?:istry)?\s*(\d{3})\b', '160'),
        (r'\bbio(?:logy)?\s*(\d{3})\b', '119'),
        (r'\becon(?:omics)?\s*(\d{3})\b', '220'),
        (r'\bpsych(?:ology)?\s*(\d{3})\b', '830'),
    ]
    
    for pattern, subj in patterns:
        for match in re.finditer(pattern, text.lower()):
            key = f"{subj}:{match.group(1)}"
            if key not in seen and scheduler.get_course(key):
                found.append(key)
                seen.add(key)
    
    return found


def extract_core_codes(text: str) -> List[str]:
    """Extract SAS core codes from text"""
    codes = []
    text_upper = text.upper()
    
    # Explicit codes
    for code in SAS_CORE_CODES.keys():
        if code in text_upper:
            codes.append(code)
    
    # Natural language
    code_keywords = {
        'quantitative': ['QQ', 'QR'],
        'math requirement': ['QQ'],
        'writing': ['WCd', 'WCr'],
        'natural science': ['NS'],
        'science requirement': ['NS'],
        'social': ['SCL'],
        'history': ['HST'],
        'historical': ['HST'],
        'diversity': ['CCD'],
        'arts': ['AHo'],
        'humanities': ['AHp', 'AHq'],
        'literature': ['AHp'],
        'philosophy': ['AHq'],
        'contemporary': ['CCO'],
        'global': ['CCO'],
        'information': ['ITR'],
        'technology': ['ITR'],
    }
    
    text_lower = text.lower()
    for keyword, matched_codes in code_keywords.items():
        if keyword in text_lower:
            codes.extend(matched_codes)
    
    return list(set(codes))


# ============================================
# MAIN CHAT PROCESSING
# ============================================

scheduler = None

def init_scheduler():
    global scheduler
    if scheduler is None:
        scheduler = RutgersScheduler()
    return scheduler


def process_chat(msg: str, history: List, image=None) -> Tuple[str, str]:
    global scheduler
    scheduler = init_scheduler()
    
    if not msg:
        return "Please enter a request!", ""
    
    msg_lower = msg.lower()
    
    # Extract info
    explicit_courses = parse_courses(msg, scheduler)
    prefs = extract_prefs(msg)
    subject = detect_subject(msg)
    core_codes = extract_core_codes(msg)
    
    # Determine intent
    wants_schedule = any(x in msg_lower for x in [
        'schedule', 'build', 'create', 'give', 'courses', 'recommend', 
        'take', 'plan', 'fill', 'need'
    ])
    wants_info = any(x in msg_lower for x in ['about', 'info', 'what is', 'tell me about', 'details'])
    wants_core = any(x in msg_lower for x in ['core', 'sas', 'requirement', 'gen ed', 'general education'])
    is_freshman = any(x in msg_lower for x in ['freshman', 'first year', 'first-year', 'new student', 'incoming'])
    
    # Extract credit target
    target = TARGET_CREDITS
    cr_match = re.search(r'(\d{1,2})\s*credits?', msg_lower)
    if cr_match:
        target = min(max(int(cr_match.group(1)), 12), 18)
    elif any(x in msg_lower for x in ['light', 'easy']):
        target = 12
    elif any(x in msg_lower for x in ['heavy', 'full', 'max']):
        target = 17
    
    # CASE 1: Course info request
    if explicit_courses and wants_info and not wants_schedule:
        info = scheduler.format_course_info(explicit_courses[0])
        
        if HF_CLIENT:
            llm_response = call_llm(
                f"Course info:\n{info}\n\nUser question: {msg}\n\nProvide helpful context (2-3 sentences).",
                "You are a helpful Rutgers academic advisor."
            )
            if llm_response:
                info += f"\n\n---\n### 💡 Advisor Notes\n{llm_response}"
        
        return info, ""
    
    # CASE 2: SAS Core / General education request
    if wants_core and (not explicit_courses or core_codes):
        # Determine which cores to fill
        if core_codes:
            target_cores = core_codes
        else:
            # Default freshman core mix
            target_cores = ['QQ', 'WCd', 'SCL', 'NS', 'HST']
        
        result = scheduler.build_core_schedule(target_cores, prefs, target)
        
        title = "SAS Core Schedule"
        text_response = f"# 🎓 {title}\n\n"
        text_response += f"**Filling Core Requirements:** {', '.join(target_cores)}\n"
        text_response += f"**All courses below have NO prerequisites** - safe for freshmen!\n\n"
        text_response += scheduler.format_schedule(result)
        
        # Add core fulfillment summary
        text_response += "\n\n## 📋 Core Requirements Satisfied\n"
        for sec in result['schedule']:
            course = scheduler.get_course(sec.get('course_key', ''))
            if course and course.get('core_codes'):
                text_response += f"- **{course.get('title')}**: {', '.join(course['core_codes'])}\n"
        
        visual = generate_visual_schedule(result['schedule'], scheduler, title)
        return text_response, visual
    
    # CASE 3: Specific core code search
    core_match = re.search(r'\b(QR|QQ|NS|HST|SCL|CCD|CCO|AH[opqr]?|WC[rd]?|ITR)\b', msg, re.I)
    if core_match and not wants_schedule:
        code = core_match.group(1).upper()
        keys = scheduler.get_courses_by_core(code)[:15]
        
        lines = [f"# Courses Satisfying {code} ({SAS_CORE_CODES.get(code, '')})\n"]
        lines.append("*Sorted by availability, no-prerequisite courses first*\n")
        
        for k in keys:
            c = scheduler.get_course(k)
            if c:
                open_ct = sum(1 for s in c.get('sections', []) if s and s.get('is_open'))
                prereq_badge = "✓ No Prereq" if not c.get('prerequisites') else "📋 Has Prereq"
                lines.append(f"- **{c.get('title')}** ({k}) - {c.get('credits')}cr, {open_ct} open | {prereq_badge}")
        
        return "\n".join(lines), ""
    
    # CASE 4: Schedule building
    if wants_schedule or explicit_courses or subject:
        courses_to_schedule = []
        
        # Add explicit courses
        courses_to_schedule.extend(explicit_courses)
        
        # Add subject-specific courses if no explicit courses
        if subject and not explicit_courses:
            # Get intro courses without prereqs
            subject_courses = scheduler.get_courses_by_subject(subject, freshman_safe=is_freshman)
            courses_to_schedule.extend(subject_courses[:2])
        
        # Build schedule
        result = scheduler.build_schedule(
            courses_to_schedule, prefs, False, target,
            freshman_safe=is_freshman
        )
        
        # Format response
        subj_name = SUBJECT_CODES.get(subject, '') if subject else ''
        title = f"{subj_name} Schedule" if subj_name else "Your Schedule"
        
        text_response = f"# 🎓 {title}\n\n"
        
        # Add freshman safety note
        if is_freshman:
            text_response += "**🎒 Freshman Mode:** Only courses with no prerequisites are auto-added.\n\n"
        
        # Add LLM advice
        if HF_CLIENT and result['schedule']:
            course_list = ", ".join([s.get('course_key', '') for s in result['schedule']])
            llm_advice = call_llm(
                f"A Rutgers student is taking: {course_list} ({result['total_credits']} credits). "
                f"Give brief advice about this schedule (2-3 sentences). Note any good choices.",
                "You are a friendly Rutgers academic advisor."
            )
            if llm_advice:
                text_response += f"💡 {llm_advice}\n\n---\n\n"
        
        text_response += scheduler.format_schedule(result)
        visual = generate_visual_schedule(result['schedule'], scheduler, title)
        
        return text_response, visual
    
    # CASE 5: General question - use LLM
    if HF_CLIENT:
        context = """You are the Rutgers Course Scheduler assistant. You help with:

1. **Building schedules**: "CS major freshman give me a schedule", "fill my SAS core"
2. **Finding courses**: "find QR courses", "what satisfies NS requirement"
3. **Course info**: "tell me about 198:111"

SAS Core Requirements:
- QQ: Quantitative Math | QR: Quantitative Reasoning  
- NS: Natural Science | SCL: Social Analysis
- HST: Historical | WCd/WCr: Writing
- AHo/AHp/AHq: Arts & Humanities | CCD: Diversity | CCO: Contemporary

Always recommend courses WITHOUT prerequisites for freshmen.
Suggest what the user might want to do based on their question."""
        
        llm_response = call_llm(msg, context)
        if llm_response:
            return llm_response, ""
    
    # Fallback help
    return """# 🎓 Rutgers Smart Scheduler

**Build a schedule:**
```
I'm a CS freshman, give me courses
Fill my SAS core requirements as a freshman
Economics major, no Friday classes
```

**Find core courses:**
```
What courses satisfy QR?
Find NS courses with no prereqs
```

**Get course info:**
```
Tell me about 198:111
```

## SAS Core Codes
- **QQ/QR**: Math & Reasoning
- **NS**: Natural Science  
- **SCL**: Social Analysis
- **HST**: Historical Analysis
- **WCd/WCr**: Writing
- **AHo/AHp/AHq**: Arts & Humanities
- **CCD/CCO**: Contemporary Challenges
- **ITR**: Information Technology

All auto-added courses are **prerequisite-free** and safe for freshmen!
""", ""


# ============================================
# GRADIO UI
# ============================================

def create_ui():
    import gradio as gr
    
    gradio_version = int(gr.__version__.split('.')[0])
    is_gradio_6 = gradio_version >= 6
    
    with gr.Blocks(title="Rutgers Course Scheduler") as demo:
        
        gr.Markdown("# 🎓 Rutgers Smart Scheduler\nPrerequisite-aware scheduling with SAS Core support")
        
        with gr.Row():
            with gr.Column(scale=2):
                msg = gr.Textbox(
                    placeholder="Try: 'Fill my SAS core as a freshman' or 'CS major no Friday'",
                    lines=2, label="What do you need?"
                )
                with gr.Row():
                    send_btn = gr.Button("🚀 Build Schedule", variant="primary", scale=2)
                    clear_btn = gr.Button("Clear", scale=1)
        
        with gr.Row():
            gr.Button("📚 Fill SAS Core").click(lambda: "Fill my SAS core requirements as a freshman", outputs=[msg])
            gr.Button("💻 CS Freshman").click(lambda: "Computer science freshman, give me courses", outputs=[msg])
            gr.Button("🔬 Science Core").click(lambda: "Find courses that satisfy NS requirement", outputs=[msg])
            gr.Button("✍️ Writing Req").click(lambda: "What satisfies the writing requirement WCd?", outputs=[msg])
        
        visual_output = gr.HTML(
            value="""<div style='padding:80px; text-align:center; color:#6c757d; 
                     background: linear-gradient(135deg, #f8f9fa, #e9ecef); border-radius:20px;'>
                     <div style='font-size:72px;'>📅</div>
                     <div style='font-size:24px; font-weight:600;'>Your Visual Schedule</div>
                     <div style='font-size:14px; margin-top:12px;'>All auto-added courses have NO prerequisites</div>
                </div>""",
            label=""
        )
        
        gr.Markdown("---")
        chatbot = gr.Chatbot(height=300, label="Schedule Details & Advice")
        
        def respond(message, history):
            if not message:
                return history, "", "<div style='padding:60px; text-align:center;'>Enter a request</div>"
            
            text_resp, visual = process_chat(message, history)
            history = history or []
            
            if is_gradio_6:
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": text_resp})
            else:
                history.append((message, text_resp))
            
            if not visual:
                visual = "<div style='padding:60px; text-align:center;'>No visual schedule</div>"
            
            return history, "", visual
        
        send_btn.click(respond, [msg, chatbot], [chatbot, msg, visual_output])
        msg.submit(respond, [msg, chatbot], [chatbot, msg, visual_output])
        clear_btn.click(lambda: ([], "", "<div style='padding:60px; text-align:center;'>📅</div>"),
                       outputs=[chatbot, msg, visual_output])
    
    return demo


if __name__ == "__main__":
    import gradio as gr
    print("=" * 60)
    print("🎓 Rutgers Smart Scheduler")
    print("   - Prerequisite checking enabled")
    print("   - SAS Core support")
    print("=" * 60)
    init_scheduler()
    print("\n🌐 Starting at http://localhost:7860\n")
    create_ui().launch(server_name="0.0.0.0", server_port=7860)