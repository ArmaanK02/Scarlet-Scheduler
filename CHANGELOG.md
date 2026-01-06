# Changelog & Documentation

This document contains all improvements, fixes, and feature additions to the Rutgers Course Scheduler.

## Recent Updates

### Course History Feature (Latest)
- Added UI for users to input courses they've already taken
- Backend API for storing/retrieving course history
- Smart recommendations based on prerequisites
- Shows fulfilled SAS core requirements
- Recommends next courses user can take

### Schedule Visualizer Fix
- Fixed "Could not generate schedule grid" error
- Added day normalization (handles "M", "Monday", etc.)
- Improved time parsing and error handling
- Better validation for schedule data structure

### Bot Improvements
- Fixed course pattern matching (microeconomics vs macroeconomics)
- Added already-taken course detection from messages
- Improved subject filtering for list requests
- Added sophomore detection (allows prerequisites)
- Enhanced LLM context with user information

---

## Detailed Changes

### 1. Course Pattern Matching Fix
**Issue:** "intro to microeconomics" incorrectly matched both 220:102 and 220:103  
**Fix:** Microeconomics now only matches 220:102, macroeconomics only matches 220:103  
**Location:** `search_courses_by_name()` function in `app.py`

### 2. Already-Taken Course Detection
**New Function:** `extract_already_taken_courses()`  
**Features:**
- Detects phrases like "already taken", "have taken", "completed"
- Extracts course names/codes from context
- Filters out these courses from suggestions

### 3. Subject Filtering
**Issue:** When user asks for "economics classes", bot added unrelated courses  
**Fix:** Added `wants_list()` function to distinguish list requests from schedule requests  
**Impact:** List requests now return filtered course lists, not schedules

### 4. Sophomore Detection
**Issue:** Bot treated all students as freshmen (too restrictive)  
**Fix:** Detects "sophomore" and allows prerequisites  
**Impact:** Sophomores can now see intermediate/advanced courses

### 5. SAS Classes Interpretation
**Issue:** "SAS classes" wasn't recognized as core requirements  
**Fix:** Added "sas classes" to core requirement detection

### 6. Enhanced LLM Context
**Issue:** LLM didn't know about user's context  
**Fix:** Improved prompts include:
- Student year (freshman/sophomore)
- Already-taken courses
- Subject interests
- Core requirements

### 7. Auto-Fill Control
**Issue:** Bot auto-filled courses even when user requested specific courses  
**Fix:** Disabled auto-fill when explicit courses are provided  
**Impact:** Bot respects user's specific course requests

### 8. Schedule Visualizer
**Fixes:**
- Added day normalization in JavaScript
- Improved time slot generation
- Fixed day matching in schedule formatter
- Added validation for schedule data structure

### 9. Course History Feature
**New Features:**
- UI panel for entering course codes
- Backend API for storage
- Prerequisite-based recommendations
- Core requirement tracking
- Next course suggestions

---

## Hugging Face Token Usage

The token is only used when:
1. **Course Info Requests** - User asks "tell me about 198:111"
2. **Schedule Building** - Only if schedule is successfully built (not empty)
3. **General Questions** - Fallback for unclear requests

**The token is NOT used for:**
- Simple list requests (rule-based filtering)
- Empty/failed schedules
- Requests that match specific patterns

**To debug LLM usage**, add to `.env`:
```env
DEBUG_LLM=true
```

---

## File Structure

### Core Files
- `app.py` - Main application (includes schedule formatter)
- `course_json_scraper.py` - Scrapes courses from Rutgers SIS API
- `data_converter.py` - Converts API data to bot format
- `update_course_data.py` - Integrated update workflow

### Frontend
- `templates/index.html` - Web UI template
- `static/app.js` - Frontend JavaScript
- `static/style.css` - Styling

### Configuration
- `requirements.txt` - Python dependencies
- `run.bat` - Windows startup script
- `.env` - Configuration (create this)

---

## Usage

### Running the Application
```bash
run.bat
```

Or manually:
```bash
venv\Scripts\activate
python app.py
```

### Updating Course Data
```bash
python update_course_data.py
```

### Course History
1. Click "Show" on "My Course History" panel
2. Enter course codes (e.g., `220:102, 220:103`)
3. Click "Save Course History"
4. Bot will use this for smarter recommendations

---

## Testing

### Test Case 1: Economics Sophomore
```
Input: "i am an economics sophomore who has already taken intro to microeconomics and intro to macroeconomics, what should i now take that has economic classes and sas classes"

Expected:
✅ Excludes 220:102 and 220:103
✅ Shows economics courses beyond intro level
✅ Includes SAS core requirement courses
✅ Allows prerequisites (sophomore mode)
```

### Test Case 2: List Request
```
Input: "give me a list of open economics classes"

Expected:
✅ Returns list format (not schedule)
✅ Only economics courses (220:xxx)
✅ Excludes already-taken courses
✅ No auto-filling
```

---

## Future Enhancements

1. **Database Storage** - Move course history to database
2. **Major Tracking** - Track progress toward major requirements
3. **Course Sequences** - Suggest full course sequences
4. **Grade Tracking** - Optional grade input for GPA
5. **Export/Import** - Export course history to file

---

## Notes

- Course history is session-based (in-memory on backend)
- Prerequisite checking is simplified (checks for course codes in text)
- More complex prerequisite logic can be added later
- All documentation consolidated into this file

