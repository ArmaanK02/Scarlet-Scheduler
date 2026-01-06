"""
Course JSON Scraper for Rutgers University
Scrapes course data from the SIS JSON API endpoint by iterating through all subject codes.
"""

import requests
import pandas as pd
import json
import time
from typing import List, Dict, Any
import os
from datetime import datetime

# All subject codes extracted from the programs of study list
# Format: "Subject Name (XXX)" - we extract the XXX codes
SUBJECT_CODES = [
    "001", "010", "011", "013", "014", "015", "016", "020", "035", "047",
    "050", "067", "070", "074", "078", "080", "081", "082", "090", "098",
    "115", "117", "119", "122", "125", "126", "136", "140", "146", "155",
    "158", "160", "165", "170", "175", "180", "185", "189", "190", "192",
    "193", "195", "198", "202", "203", "206", "207", "211", "216", "219",
    "220", "300", "332", "351", "355", "356", "358", "359", "360", "364",
    "370", "373", "374", "375", "377", "381", "382", "390", "400", "420",
    "440", "447", "450", "460", "470", "489", "490", "501", "505", "506",
    "508", "510", "512", "522", "533", "535", "540", "547", "550", "554",
    "556", "557", "558", "560", "563", "565", "567", "573", "574", "575",
    "580", "590", "595", "607", "615", "617", "620", "624", "628", "630",
    "635", "640", "650", "652", "667", "670", "680", "685", "690", "691",
    "692", "694", "700", "701", "705", "709", "713", "715", "718", "720",
    "721", "723", "725", "730", "750", "775", "776", "787", "790", "799",
    "810", "830", "832", "833", "840", "843", "851", "860", "888", "902",
    "904", "907", "910", "920", "940", "955", "959", "960", "965", "966",
    "971", "973", "975", "988", "991"
]


def get_semester_code(year: str, semester: str) -> str:
    """
    Construct semester code from year and semester.
    Spring: 1 + year (e.g., 12026 for Spring 2026)
    Fall: 9 + year (e.g., 92026 for Fall 2026)
    """
    semester = semester.lower().strip()
    if semester == "spring":
        return f"1{year}"
    elif semester == "fall":
        return f"9{year}"
    else:
        raise ValueError(f"Invalid semester: {semester}. Must be 'spring' or 'fall'.")


def scrape_course_data(subject_code: str, semester_code: str, campus: str = "NB", level: str = "UG") -> List[Dict[str, Any]]:
    """
    Scrape course data from the Rutgers SIS JSON API for a specific subject.
    
    Args:
        subject_code: 3-digit subject code (e.g., "198" for Computer Science)
        semester_code: Semester code (e.g., "12026" for Spring 2026)
        campus: Campus code (default: "NB" for New Brunswick)
        level: Level code (default: "UG" for Undergraduate)
    
    Returns:
        List of course dictionaries, or empty list if error
    """
    url = f"https://sis.rutgers.edu/oldsoc/courses.json"
    params = {
        "subject": subject_code,
        "semester": semester_code,
        "campus": campus,
        "level": level
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Add subject code and semester to each course for tracking
        for course in data:
            course["scraped_subject_code"] = subject_code
            course["scraped_semester_code"] = semester_code
            course["scraped_campus"] = campus
            course["scraped_level"] = level
        
        return data if isinstance(data, list) else []
    
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Error fetching subject {subject_code}: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        print(f"  ⚠ Invalid JSON for subject {subject_code}: {str(e)}")
        return []
    except Exception as e:
        print(f"  ⚠ Unexpected error for subject {subject_code}: {str(e)}")
        return []


def flatten_course_data(courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten nested course data structure for easier spreadsheet viewing.
    Expands sections and other nested structures into separate rows.
    """
    flattened = []
    
    for course in courses:
        base_course = {
            "subject": course.get("subject"),
            "courseNumber": course.get("courseNumber"),
            "title": course.get("title"),
            "expandedTitle": course.get("expandedTitle"),
            "credits": course.get("credits"),
            "synopsisUrl": course.get("synopsisUrl"),
            "preReqNotes": course.get("preReqNotes"),
            "courseDescription": course.get("courseDescription"),
            "scraped_subject_code": course.get("scraped_subject_code"),
            "scraped_semester_code": course.get("scraped_semester_code"),
            "scraped_campus": course.get("scraped_campus"),
            "scraped_level": course.get("scraped_level"),
            "openSections": course.get("openSections"),
            "campusCode": course.get("campusCode"),
        }
        
        # Handle core codes
        core_codes = course.get("coreCodes", [])
        if core_codes:
            base_course["coreCodes"] = ", ".join([cc.get("code", "") for cc in core_codes])
            base_course["coreCodeDescriptions"] = ", ".join([cc.get("coreCodeDescription", "") for cc in core_codes])
        else:
            base_course["coreCodes"] = ""
            base_course["coreCodeDescriptions"] = ""
        
        # Expand sections - create a row for each section
        sections = course.get("sections", [])
        
        if not sections:
            # Course with no sections - add as single row
            flattened.append(base_course.copy())
        else:
            # Create a row for each section
            for section in sections:
                section_row = base_course.copy()
                section_row["sectionNumber"] = section.get("number")
                section_row["sectionIndex"] = section.get("index")
                section_row["sectionOpenStatus"] = section.get("openStatus")
                section_row["sectionNotes"] = section.get("sectionNotes")
                section_row["examCode"] = section.get("examCode")
                
                # Handle instructors
                instructors = section.get("instructors", [])
                section_row["instructors"] = ", ".join([inst.get("name", "") for inst in instructors])
                
                # Handle meeting times
                meeting_times = section.get("meetingTimes", [])
                if meeting_times:
                    mt_list = []
                    for mt in meeting_times:
                        mt_str = f"{mt.get('meetingDay', '')} {mt.get('startTime', '')}-{mt.get('endTime', '')} {mt.get('buildingCode', '')} {mt.get('roomNumber', '')} ({mt.get('meetingModeDesc', '')})"
                        mt_list.append(mt_str.strip())
                    section_row["meetingTimes"] = " | ".join(mt_list)
                else:
                    section_row["meetingTimes"] = ""
                
                section_row["campusLocation"] = meeting_times[0].get("campusName", "") if meeting_times else ""
                
                flattened.append(section_row)
    
    return flattened


def main():
    """
    Main function to orchestrate the scraping process.
    """
    print("=" * 70)
    print(" " * 15 + "RUTGERS COURSE JSON SCRAPER")
    print("=" * 70)
    print(f"\nTotal subject codes to process: {len(SUBJECT_CODES)}")
    
    # Get user input for year and semester
    print("\n" + "=" * 70)
    print("SEMESTER INFORMATION")
    print("=" * 70)
    
    year = input("Enter the year (e.g., 2026): ").strip()
    if not year:
        print("❌ Year is required. Exiting.")
        return
    
    semester = input("Enter the semester (spring/fall): ").strip().lower()
    if semester not in ["spring", "fall"]:
        print("❌ Invalid semester. Must be 'spring' or 'fall'. Exiting.")
        return
    
    semester_code = get_semester_code(year, semester)
    print(f"\n✓ Semester code: {semester_code} ({semester.capitalize()} {year})")
    
    # Ask for campus (optional, defaults to NB)
    campus = input("\nEnter campus code (default: NB for New Brunswick): ").strip().upper()
    if not campus:
        campus = "NB"
    
    # Ask for level (optional, defaults to UG)
    level = input("Enter level code (default: UG for Undergraduate): ").strip().upper()
    if not level:
        level = "UG"
    
    print("\n" + "=" * 70)
    print("SCRAPING PROCESS")
    print("=" * 70)
    print(f"Subject codes: {len(SUBJECT_CODES)}")
    print(f"Semester: {semester_code} ({semester.capitalize()} {year})")
    print(f"Campus: {campus}")
    print(f"Level: {level}")
    
    # Confirm before starting
    confirm = input("\nProceed with scraping? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("❌ Scraping cancelled.")
        return
    
    # Scrape all subjects
    all_courses = []
    successful_scrapes = 0
    failed_scrapes = 0
    
    print("\n" + "=" * 70)
    print("SCRAPING IN PROGRESS...")
    print("=" * 70)
    
    start_time = time.time()
    
    for i, subject_code in enumerate(SUBJECT_CODES, 1):
        print(f"\n[{i}/{len(SUBJECT_CODES)}] Scraping subject code: {subject_code}...", end=" ")
        
        courses = scrape_course_data(subject_code, semester_code, campus, level)
        
        if courses:
            all_courses.extend(courses)
            successful_scrapes += 1
            print(f"✓ Found {len(courses)} course(s)")
        else:
            failed_scrapes += 1
            print("✗ No data or error")
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.5)
        
        # Progress update every 10 subjects
        if i % 10 == 0:
            elapsed = time.time() - start_time
            print(f"\n  Progress: {i}/{len(SUBJECT_CODES)} subjects | "
                  f"Success: {successful_scrapes} | Failed: {failed_scrapes} | "
                  f"Time: {elapsed:.1f}s")
    
    elapsed_time = time.time() - start_time
    
    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE")
    print("=" * 70)
    print(f"Total subjects processed: {len(SUBJECT_CODES)}")
    print(f"Successful: {successful_scrapes}")
    print(f"Failed/Empty: {failed_scrapes}")
    print(f"Total courses found: {len(all_courses)}")
    print(f"Total time: {elapsed_time:.1f} seconds")
    
    if not all_courses:
        print("\n❌ No course data found. Exiting.")
        return
    
    # Flatten the data for spreadsheet
    print("\n📊 Flattening course data...")
    flattened_data = flatten_course_data(all_courses)
    print(f"✓ Created {len(flattened_data)} rows (expanded sections)")
    
    # Create DataFrame
    df = pd.DataFrame(flattened_data)
    
    # Generate output filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    semester_str = f"{semester.capitalize()}{year}"
    csv_filename = f"rutgers_courses_{semester_str}_{campus}_{timestamp}.csv"
    json_filename = f"rutgers_courses_{semester_str}_{campus}_{timestamp}.json"
    excel_filename = f"rutgers_courses_{semester_str}_{campus}_{timestamp}.xlsx"
    
    # Save to CSV
    print(f"\n💾 Saving to CSV: {csv_filename}...")
    df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"✓ CSV saved: {csv_filename}")
    
    # Save to JSON (original format)
    print(f"💾 Saving to JSON: {json_filename}...")
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_courses, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON saved: {json_filename}")
    
    # Save to Excel
    try:
        print(f"💾 Saving to Excel: {excel_filename}...")
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        print(f"✓ Excel saved: {excel_filename}")
    except ImportError:
        print("⚠ openpyxl not installed. Skipping Excel export.")
        print("  Install with: pip install openpyxl")
    except Exception as e:
        print(f"⚠ Error saving Excel file: {str(e)}")
    
    # Summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    print(f"Total courses: {len(all_courses)}")
    print(f"Total sections: {len(flattened_data)}")
    
    if "subject" in df.columns:
        unique_subjects = df["subject"].nunique()
        print(f"Unique subjects: {unique_subjects}")
    
    if "openSections" in df.columns:
        total_open_sections = df["openSections"].sum() if df["openSections"].dtype in ['int64', 'float64'] else 0
        print(f"Total open sections: {total_open_sections}")
    
    print("\n" + "=" * 70)
    print("✓ SCRAPING COMPLETE!")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"  - {csv_filename}")
    print(f"  - {json_filename}")
    if os.path.exists(excel_filename):
        print(f"  - {excel_filename}")


if __name__ == "__main__":
    main()

