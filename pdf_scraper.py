import json
import re
import os
import sys

# Try to import pypdf
try:
    from pypdf import PdfReader
except ImportError:
    print("Error: pypdf not installed. Please run: pip install pypdf")
    sys.exit(1)

def scrape_catalog_pdf(pdf_filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, pdf_filename)
    output_path = os.path.join(script_dir, 'major_requirements.json')

    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF not found at: {pdf_path}")
        return

    print(f"✅ Reading {pdf_filename}...")
    try:
        reader = PdfReader(pdf_path)
        full_text = ""
        
        # --- PHASE 1: FULL TEXT EXTRACTION ---
        # We need the full text for requirements searching later
        print(f"  Document has {len(reader.pages)} pages. Scanning all...")
        for i, page in enumerate(reader.pages):
            full_text += page.extract_text() + "\n"
            if i % 200 == 0: print(f"    Processed {i} pages...")

        catalog_db = {
            "majors": {},
            "minors": {},
            "certificates": {}
        }

        # --- PHASE 2: SUMMARY LIST PARSING (Page Range Strategy) ---
        # Based on user info:
        # Majors: Pages 14-16 (Index 13-15)
        # Minors: Pages 17-19 (Index 16-18)
        # Certs:  Pages 20-23 (Index 19-22)
        
        print("  Parsing Summary Lists from specific page ranges...")

        def parse_pages(start_page, end_page, category_key):
            # pypdf is 0-indexed, so Page 14 is index 13
            start_idx = start_page - 1
            end_idx = end_page # slice is exclusive
            
            chunk_text = ""
            for i in range(start_idx, end_idx):
                if i < len(reader.pages):
                    chunk_text += reader.pages[i].extract_text() + "\n"
            
            lines = chunk_text.split('\n')
            count = 0
            
            school_map = {
                "": "SAS", "*": "SEBS", "**": "MGSA", "***": "SMLR", 
                "****": "EJB", "*****": "GSE", "******": "SCI", 
                "*******": "RBS", "********": "SAS/SCI"
            }

            for line in lines:
                line = line.strip()
                # Remove bullets
                clean_line = line.replace('•', '').strip()
                
                # Filters
                if len(clean_line) < 4: continue
                if "Rutgers University" in clean_line: continue
                if "Programs of Study" in clean_line: continue
                if re.match(r'^\d+\s*/\s*\d+$', clean_line): continue # Page nums
                
                # Parse Name and School (Asterisks)
                # Look for asterisks at the end
                match = re.search(r'([^*]+)(\*+)$', clean_line)
                if match:
                    name = match.group(1).strip()
                    stars = match.group(2)
                    school = school_map.get(stars, "Unknown")
                else:
                    name = clean_line
                    school = "SAS" # Default
                
                # Store
                if name not in catalog_db[category_key]:
                    catalog_db[category_key][name] = {"school": school, "requirements": []}
                    count += 1
            
            print(f"    Pages {start_page}-{end_page}: Found {count} {category_key}.")

        # Run Parsers
        parse_pages(14, 17, "majors")
        parse_pages(17, 20, "minors")
        parse_pages(20, 24, "certificates")

        print(f"  Total Discovered: {len(catalog_db['majors'])} Majors, {len(catalog_db['minors'])} Minors, {len(catalog_db['certificates'])} Certificates.")

        # --- PHASE 3: REQUIREMENTS EXTRACTION ---
        print("  Extracting requirements (course codes)...")
        
        # Helper to find reqs in the full text body
        def extract_reqs(name):
            # Heuristic: Find "Name" header followed by "Requirements" within 5000 chars
            # We skip the TOC area (first 100k chars) to avoid finding the list itself
            body_text = full_text[100000:]
            
            header_regex = re.compile(rf"{re.escape(name)}.*?(?:Requirements|Curriculum)", re.IGNORECASE)
            match = header_regex.search(body_text)
            
            if match:
                start = match.end()
                chunk = body_text[start:start+4000]
                # Find codes 000:000
                codes = re.findall(r'\b(\d{3}:\d{3})\b', chunk)
                return list(set(codes))[:25]
            return []

        # Update DB with requirements
        for cat in ["majors", "minors", "certificates"]:
            for name in catalog_db[cat]:
                reqs = extract_reqs(name)
                if reqs:
                    catalog_db[cat][name]["requirements"] = reqs

        # Save
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog_db, f, indent=2)
        print(f"✅ Saved catalog database to: {output_path}")

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scrape_catalog_pdf("rutgers-catalog-1746803554494.pdf")