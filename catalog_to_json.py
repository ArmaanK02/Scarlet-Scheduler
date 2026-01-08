import json

def generate_mock_db():
    """
    Generates a starter knowledge base for majors.
    """
    data = {
        "Computer Science": {
            "core": ["198:111", "198:112", "198:205", "198:206", "198:211", "198:344"],
            "electives": ["198:314", "198:323", "198:336", "198:416", "198:440"],
            "math_reqs": ["640:151", "640:152", "640:250"]
        },
        "Data Science": {
            "core": ["198:142", "960:291", "198:210", "960:295"],
            "electives": ["198:336", "960:465"]
        },
        "Economics": {
            "core": ["220:102", "220:103", "220:320", "220:321", "220:322"],
            "electives": ["220:301", "220:308", "220:339"]
        },
        "Business": {
            "required": ["010:272", "010:275", "220:102", "220:103", "640:135", "960:285"]
        },
        "Biology": {
            "core": ["119:115", "119:116", "160:161", "160:162"],
            "labs": ["119:117", "160:171"]
        }
    }
    
    with open('major_requirements.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Generated major_requirements.json with Data Science & Economics")

if __name__ == "__main__":
    generate_mock_db()