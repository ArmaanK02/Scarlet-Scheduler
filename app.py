import os
import re
import json
import logging
import requests
import copy
from flask import Flask, render_template, request, jsonify, session
from config import get_config
from data_adapter import DataServiceFactory
from scheduler_strategies import DeepSeekSchedulerStrategy
from scheduler_core import ScheduleConstraints
from prerequisite_parser import PrerequisiteParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- PATH SETUP ---
base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
data_filename = 'rutgers_scheduler_data.json'
majors_filename = 'major_requirements.json'

# Auto-Discovery for Data File
possible_paths = [
    os.path.join(base_dir, data_filename),
    os.path.join(os.getcwd(), data_filename),
    os.path.join(os.path.dirname(base_dir), data_filename)
]
found_data_path = next((p for p in possible_paths if os.path.exists(p)), None)

Config = get_config()
if found_data_path:
    Config.DATA_FILE_PATH = found_data_path
    logger.info(f"Data file found at: {found_data_path}")

# Load Major/Minor Requirements
catalog_db = {}
major_path = os.path.join(base_dir, majors_filename)
if os.path.exists(major_path):
    try:
        with open(major_path, 'r', encoding='utf-8') as f:
            catalog_db = json.load(f)
        if "majors" not in catalog_db:
            catalog_db = {"majors": catalog_db, "minors": {}, "certificates": {}}
        m = len(catalog_db.get('majors', {}))
        mi = len(catalog_db.get('minors', {}))
        c = len(catalog_db.get('certificates', {}))
        logger.info(f"✅ Loaded Catalog: {m} Majors, {mi} Minors, {c} Certs.")
    except Exception as e:
        logger.error(f"❌ Failed to load catalog: {e}")
else:
    logger.warning("⚠️ major_requirements.json NOT FOUND. Run pdf_scraper.py first.")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config.from_object(Config)
app.secret_key = 'dev_key_for_session'

GREETINGS = ["hello", "hi", "hey", "greetings", "sup"]

# --- GENERATIVE AI ENGINE ---

class GeminiAgent:
    def __init__(self, api_keys):
        self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        self.current_key_index = 0
        self.base_url = "https://generativelanguage.googleapis.com/v1/models"
        self.preferred_models = [
            "gemini-2.0-flash-lite-001",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-pro"
        ]
        self._discover_and_log_models()

    def _get_current_key(self):
        if not self.api_keys: return None
        return self.api_keys[self.current_key_index % len(self.api_keys)]

    def _rotate_key(self):
        if len(self.api_keys) > 1:
            self.current_key_index += 1
            logger.info(f"🔄 Rotating to API Key #{self.current_key_index % len(self.api_keys) + 1}")
            return True
        return False

    def _discover_and_log_models(self):
        """Query Google to log available models for debugging."""
        key = self._get_current_key()
        if not key or "YOUR_KEY" in key: return
        try:
            url = f"{self.base_url}?key={key}"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'].replace('models/', '') for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
                logger.info(f"🔎 Available Gemini Models: {models}")
            else:
                logger.warning(f"Failed to list models: {response.status_code}")
        except Exception as e:
            logger.error(f"Model discovery error: {e}")

    def _generate(self, prompt_text):
        attempts = 0
        max_attempts = len(self.api_keys) # Try each key once per generation request

        while attempts < max_attempts:
            current_key = self._get_current_key()
            if not current_key or "YOUR_KEY" in current_key:
                return None
            
            headers = {'Content-Type': 'application/json'}
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            
            # Iterate through preferred models until one works
            for model in self.preferred_models:
                url = f"{self.base_url}/{model}:generateContent?key={current_key}"
                try:
                    response = requests.post(url, headers=headers, json=payload)
                    
                    # Success
                    if response.status_code == 200:
                        data = response.json()
                        if 'candidates' in data and data['candidates']:
                            logger.info(f"✅ Success with model: {model} (Key #{self.current_key_index + 1})")
                            return data['candidates'][0]['content']['parts'][0]['text']
                    
                    # Handle Rate Limit (429) -> Try next model, or rotate key if all models fail
                    elif response.status_code == 429:
                        logger.warning(f"⚠️ Rate Limit (429) on {model}. Trying next model...")
                        continue 
                    
                    elif response.status_code == 404:
                        continue

                    else:
                        logger.warning(f"❌ Error {response.status_code} on {model}: {response.text[:100]}...")
                
                except Exception as e:
                    logger.error(f"Connection error on {model}: {e}")
            
            # If we exit the model loop, it means the current key failed for all models (likely rate limit or quota)
            logger.warning(f"⚠️ Key #{self.current_key_index + 1} exhausted/failed. Rotating...")
            if not self._rotate_key():
                break # No more keys to try
            attempts += 1

        logger.error("❌ All keys and models failed.")
        return None

    def analyze_intent(self, user_text, history_context="", major_context=""):
        prompt = f"""
        You are an expert Rutgers academic advisor.
        
        CONTEXT:
        Student History: {history_context}
        Catalog Requirements Knowledge: {major_context}
        
        TASK:
        Analyze: "{user_text}"
        
        1. Extract explicit course codes requested (e.g. "198:111").
        2. Identify subjects mentioned (e.g. "Computer Science").
        3. **IMPORTANT**: If a Major/Minor is mentioned, OR if the user asks to "fill my schedule", ONLY THEN suggest 2-3 specific courses required that are NOT in the student history. 
           If the user just asks for specific classes (e.g. "Schedule CS 111 and Calc 1"), DO NOT add extra classes unless asked.
        4. Extract constraints ONLY if explicitly stated (e.g. "No Friday", "No Mornings"). Do not assume constraints.
        
        Return JSON ONLY:
        {{
            "codes": ["198:111", ...],
            "subjects": ["Computer Science", ...],
            "constraints": ["No Friday", ...],
            "is_conversational": boolean,
            "explanation": "Brief explanation of choices."
        }}
        """
        raw_text = self._generate(prompt)
        if not raw_text: return None
        try:
            text = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except: return None

    def chat_fallback(self, user_text):
        return self._generate(f"You are a helpful Rutgers scheduler. Reply to: {user_text}") or "I'm having trouble thinking right now."

    def explain_failure(self, failed_codes, constraints):
        prompt = f"""
        I failed to schedule these courses: {failed_codes} with constraints: {constraints}.
        
        Write a short message to the student explaining that these specific classes likely conflict.
        Do NOT suggest checking the catalog. Just state that a valid combination wasn't found.
        Mention that I have tried relaxing constraints to find other options.
        """
        return self._generate(prompt)

    def summarize_success(self, found_codes, constraints, count):
        prompt = f"""
        I successfully generated {count} schedules for: {found_codes}.
        Constraints applied: {constraints}.
        
        Write a very short, cheerful confirmation.
        """
        return self._generate(prompt)

ai_agent = GeminiAgent(Config.GEMINI_API_KEYS)

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parse_history', methods=['POST'])
def parse_history():
    try:
        data = request.get_json()
        raw_text = data.get('text', '')
        taken_courses = PrerequisiteParser.parse_copy_paste(raw_text)
        repo = DataServiceFactory.get_repository()
        lookup_map = {}
        if hasattr(repo, 'data_cache'):
            for c in repo.data_cache:
                s = str(c.get('subject', ''))
                n = str(c.get('courseNumber', ''))
                lookup_map[f"{s}:{n}"] = c.get('title', '')
        for c in taken_courses:
            c['title'] = lookup_map.get(c['short_code'], 'Unknown Title')
        session['course_history'] = taken_courses
        return jsonify({'message': f"Imported {len(taken_courses)} courses.", 'courses': taken_courses})
    except Exception as e:
        logger.error(f"Parse Error: {e}")
        return jsonify({'message': 'Failed to parse text.'}), 500

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json(force=True, silent=True) or {}
        text_input = str(data.get('message') or data.get('text') or "").strip()
        if not text_input: return jsonify({'message': "Please type something!"})

        logger.info(f"User Query: {text_input}")
        
        history = session.get('course_history', [])
        history_codes = [h['short_code'] for h in history] if history else []
        history_str = ", ".join(history_codes)

        full_major_context = ""
        lower_input = text_input.lower()
        for category in ["majors", "minors", "certificates"]:
            cat_data = catalog_db.get(category, {})
            for name, details in cat_data.items():
                if name.lower() in lower_input:
                    full_major_context += f"{category[:-1].capitalize()} in {name} ({details.get('school','?')}) Reqs: {json.dumps(details)}. "

        ai_result = ai_agent.analyze_intent(text_input, history_context=history_str, major_context=full_major_context)
        logger.info(f"AI Analysis: {ai_result}")
        
        if not ai_result:
            local_codes = re.findall(r'(\d{3})[:\s\-](\d{3})', text_input)
            ai_result = {
                "codes": [f"{m[0]}:{m[1]}" for m in local_codes],
                "subjects": [],
                "constraints": [],
                "is_conversational": any(g in lower_input for g in GREETINGS),
                "explanation": ""
            }

        if ai_result.get("is_conversational") and not ai_result.get("codes") and not ai_result.get("subjects"):
            reply = ai_agent.chat_fallback(text_input)
            return jsonify({'message': reply, 'schedules': []})

        final_codes = ai_result.get("codes", [])
        subjects = ai_result.get("subjects", [])
        explanation = ai_result.get("explanation", "")
        
        final_codes = PrerequisiteParser.filter_completed_courses(final_codes, history)
        
        raw_constraints = ai_result.get("constraints", [])
        local_no_days = []
        for c in raw_constraints:
            c = c.lower()
            if "fri" in c: local_no_days.append("F")
            if "mon" in c: local_no_days.append("M")
            if "tue" in c: local_no_days.append("T")
            if "wed" in c: local_no_days.append("W")
            if "thu" in c: local_no_days.append("TH")
        
        # --- MULTI-PASS SCHEDULING STRATEGY ---
        
        repo = DataServiceFactory.get_repository()
        
        # Subject Resolution
        if subjects and len(final_codes) < 4: # Only auto-fill if we have few courses
            for subj in subjects:
                if "sas core" in subj.lower():
                    found = repo.search_courses("Core") 
                    if not found: found = repo.search_courses("Psychology")
                else:
                    found = repo.search_courses(subj)
                
                valid = [c for c in found if c.code not in history_codes]
                valid.sort(key=lambda x: x.code.split(':')[1])
                
                for c in valid[:3]: 
                    if c.code not in final_codes: final_codes.append(c.code)
        
        final_codes = list(set(final_codes))
        if not final_codes:
            msg = f"I couldn't find new courses. {explanation}"
            if history: msg += " (Checked against history)."
            return jsonify({'message': msg, 'schedules': []})

        courses_obj = repo.get_courses(final_codes)
        found_real_codes = [c.code for c in courses_obj]
        
        scheduler = DeepSeekSchedulerStrategy()
        
        # PASS 1: Strict Constraints
        constraints = ScheduleConstraints(no_days=list(set(local_no_days)))
        results = []
        valid_schedules = scheduler.generate_schedules(courses_obj, constraints)
        
        status_msg = ""
        
        if valid_schedules:
            # Success on Pass 1
            for schedule in valid_schedules:
                schedule_data = []
                for section in schedule:
                    course_title = "Unknown Course"
                    course_code_str = "000:000"
                    
                    for c in courses_obj:
                        for s in c.sections:
                            if s.index == section.index:
                                course_title = c.title
                                course_code_str = c.code
                                break
                    
                    schedule_data.append({
                        'course': course_code_str,
                        'title': course_title,
                        'index': section.index,
                        'instructors': section.instructors,
                        'times': [str(t) for t in section.time_slots]
                    })
                results.append(schedule_data)
                
            ai_success_msg = ai_agent.summarize_success(found_real_codes, raw_constraints, len(results))
            status_msg = ai_success_msg if ai_success_msg else f"Success! Found {len(results)} options."
            
        else:
            # Failure on Pass 1 -> Try PASS 2 (Relaxed Constraints)
            if local_no_days:
                logger.info("Pass 1 failed. Trying Pass 2 (Ignored Constraints)...")
                relaxed_constraints = ScheduleConstraints(no_days=[])
                valid_schedules_relaxed = scheduler.generate_schedules(courses_obj, relaxed_constraints)
                
                if valid_schedules_relaxed:
                    for schedule in valid_schedules_relaxed:
                        schedule_data = []
                        for section in schedule:
                            course_title = "Unknown Course"
                            course_code_str = "000:000"
                            for c in courses_obj:
                                for s in c.sections:
                                    if s.index == section.index:
                                        course_title = c.title
                                        course_code_str = c.code
                                        break

                            schedule_data.append({
                                'course': course_code_str,
                                'title': course_title,
                                'index': section.index,
                                'instructors': section.instructors,
                                'times': [str(t) for t in section.time_slots]
                            })
                        results.append(schedule_data)
                    
                    status_msg = f"I couldn't find a schedule with your constraints ({', '.join(raw_constraints)}), BUT I found {len(results)} options if you are flexible."
                else:
                    advice = ai_agent.explain_failure(found_real_codes, raw_constraints)
                    status_msg = f"I couldn't find any valid schedule even after relaxing constraints. {advice}"
            else:
                advice = ai_agent.explain_failure(found_real_codes, raw_constraints)
                status_msg = f"I couldn't find a valid combination for {', '.join(found_real_codes)}. {advice}"

        return jsonify({"message": status_msg, "schedules": results, "count": len(results)})

    except Exception as e:
        logger.error(f"Chat Error: {e}", exc_info=True)
        return jsonify({'message': 'System Error.', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=Config.DEBUG)