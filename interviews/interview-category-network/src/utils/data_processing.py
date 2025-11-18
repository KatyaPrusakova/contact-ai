def load_data(file_path):
    import json
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def extract_categories(interview_data):
    categories = set()
    for interview in interview_data:
        categories.update(interview.get('categories', []))
    return list(categories)