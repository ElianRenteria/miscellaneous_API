from fastapi import FastAPI
import json, requests
app = FastAPI()


def parse_json_from_string(string_with_json):
    # Find where the JSON starts
    start_index = string_with_json.find('{')

    if start_index == -1:
        raise ValueError("No JSON object found in the string")

    # Find where the JSON ends
    end_index = string_with_json.rfind('}') + 1

    if end_index == 0:
        raise ValueError("Invalid JSON format: No closing '}' found")

    # Extract the JSON substring
    json_string = string_with_json[start_index:end_index]

    # Parse the JSON string into a Python dictionary
    parsed_json = json.loads(json_string)

    return parsed_json

@app.get("/api")
async def root():
    return {"message": "Hello World"}


@app.get("/api/trivia")
async def generate_question():
    response = requests.post("http://elianrenteria.net:8000/generate", json={"message": "Generate me a random trivia question with the correct answer and 3 false answers and respond ONLY in json format as given here: {\"question\":\"\",\"answers\":[\"\",\"\", \"\", \"\"]} for the answers value it should be an array where the first index is the correct answer."})
    return parse_json_from_string(response.json()["response"])

