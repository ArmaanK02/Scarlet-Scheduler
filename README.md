# Scarlet Scheduler
Rutgers Course Scheduler with Prerequisite Checking

A smart course scheduling assistant that helps Rutgers students build their schedules with automatic prerequisite checking, SAS Core support, and visual schedule display.

## Quick Start

### 1. Setup (First Time Only)

```bash
# Activate virtual environment
venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Configure (Optional)

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Copy the example file
copy .env.example .env
```

Then edit `.env` and add your values:

```env
HF_TOKEN=your_huggingface_token_here
AUTO_REFRESH_DATA=true
DATA_STALE_DAYS=30
```

**⚠️ IMPORTANT:** Never commit `.env` to version control! It contains sensitive credentials.

- `HF_TOKEN`: HuggingFace token for LLM features (optional)
- `AUTO_REFRESH_DATA`: Automatically refresh course data when stale (default: false)
- `DATA_STALE_DAYS`: Days before data is considered stale (default: 30)

### 3. Update Course Data (First Time)

```bash
# Update for current semester (auto-detected)
python update_course_data.py

# Or specify semester
python update_course_data.py --year 2026 --semester spring
```

This will:
- Scrape all courses from Rutgers SIS API
- Convert to the bot's format
- Save to `rutgers_scheduler_data.json`
- Create automatic backup

### 4. Run the Application

**Option 1: Quick Start (Windows)**
```bash
run.bat
```

**Option 2: Manual**
```bash
venv\Scripts\activate
python app.py
```

The application will start at **http://localhost:7860** (or next available port).

## Usage

### Building Schedules

The bot understands natural language requests:

- **Specific courses:** "show me a schedule that has intro to microeconomics and intro to macroeconomics"
- **Course codes:** "give me a schedule with 220:102 and 220:103"
- **Subject-based:** "I'm a CS freshman, give me courses"
- **SAS Core:** "Fill my SAS core requirements as a freshman"
- **Preferences:** "Economics major, no Friday classes"

### Features

- ✅ **Prerequisite Checking** - Won't schedule courses with unmet prerequisites
- ✅ **SAS Core Support** - Intelligently fills core requirements
- ✅ **Natural Language** - Understands course names like "intro to microeconomics"
- ✅ **Visual Schedule** - Color-coded weekly calendar by campus
- ✅ **LLM-Powered** - Smart recommendations and advice
- ✅ **Freshman-Safe** - Filters courses safe for first-year students

## Updating Course Data

### Automatic Updates

If `AUTO_REFRESH_DATA=true` in `.env`, the bot automatically refreshes data when:
- The database file doesn't exist
- The database file is older than `DATA_STALE_DAYS` (default: 30)

### Manual Updates

```bash
# Update for current semester
python update_course_data.py

# Update for specific semester
python update_course_data.py --year 2026 --semester spring --campus NB --level UG
```

### Advanced: Using Scraper Directly

```bash
# Run interactive scraper
python course_json_scraper.py

# Convert scraped data
python data_converter.py rutgers_courses_Spring2026_NB_20250101_120000.json
```

## Project Structure

```
Scarlet-Scheduler/
├── app.py                      # Main application (Flask backend)
├── course_json_scraper.py      # Scrapes courses from Rutgers SIS API
├── data_converter.py           # Converts API data to bot format
├── update_course_data.py       # Integrated update workflow
├── schedule_formatter.py       # Formats schedule data for frontend
├── requirements.txt            # Python dependencies
├── .env                        # Configuration (create this)
├── rutgers_scheduler_data.json # Course database (auto-generated)
├── templates/
│   └── index.html             # Web UI template
└── static/
    ├── style.css              # Styling (red/black theme)
    └── app.js                 # Frontend JavaScript
```

## Dependencies

- `flask` - Web framework
- `huggingface_hub` - LLM features (optional)
- `requests` - API scraping
- `pandas` - Data processing
- `openpyxl` - Excel export support

## Troubleshooting

### Port Already in Use
The app automatically finds the next available port (7860, 7861, etc.)

### No Database File
Run `python update_course_data.py` to create the database, or enable `AUTO_REFRESH_DATA=true` in `.env`

### Bot Not Finding Courses
- Verify the course exists in `rutgers_scheduler_data.json`
- Try using course codes (e.g., "220:102") instead of names
- Check that the database is up-to-date for the current semester

### Auto-Refresh Not Working
- Verify `.env` file exists and has `AUTO_REFRESH_DATA=true`
- Check for typos (case-sensitive)
- Ensure `update_course_data.py` is in the same directory

## Examples

**Build schedule with specific courses:**
```
show me a schedule that has intro to microeconomics and intro to macroeconomics
```

**Subject-based schedule:**
```
I'm a computer science freshman, give me a schedule
```

**SAS Core requirements:**
```
Fill my SAS core requirements as a freshman
```

**With preferences:**
```
Economics major, no Friday classes, after 10 AM
```

## License

This project is for educational use with Rutgers University course data.
