from fastapi import FastAPI, Query, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from pydantic import BaseModel
from dotenv import load_dotenv
import os, random
import shutil
import zipfile

load_dotenv()

open_weather_key = os.getenv('OPEN_WEATHER_KEY')
generate_api_url = os.getenv('GENERATE_API_URL')
api_key = os.getenv('GENERATE_API_KEY')
generate_note_prompt = os.getenv('GENERATE_NOTE_PROMPT')

app = FastAPI()

with open('./data/wordle-words.txt', 'r') as file:
    words = file.readlines()
words = [word.strip() for word in words]

class MessageRequest(BaseModel):
    category: str

class WeatherRequest(BaseModel):
    city: str

class GenerateRequest(BaseModel):
    message: str
    key: str

class GenerateNote(BaseModel):
    student_name: str
    previous_note: str
    concepts: str

def parse_json_from_string(string_with_json):
    start_index = string_with_json.find('{')
    if start_index == -1:
        raise ValueError("No JSON object found in the string")
    end_index = string_with_json.rfind('}') + 1
    if end_index == 0:
        raise ValueError("Invalid JSON format: No closing '}' found")
    json_string = string_with_json[start_index:end_index]
    parsed_json = json.loads(json_string)
    return parsed_json


# Add CORS middleware
origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://coderlab.work",
    "https://elianrenteria.github.io"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/trivia")
async def generate_question():
    response = requests.post(generate_api_url, json={"message": "Generate me a random trivia question with the correct answer and 3 false answers and respond ONLY in json format as given here: {\"question\":\"\",\"answers\":[\"\",\"\", \"\", \"\"]} for the answers value it should be an array where the first index is the correct answer."})
    return parse_json_from_string(response.json()["response"])

@app.get("/api/wordle")
async def pick_word():
    global words
    random_word = random.choice(words)
    return {"word": random_word}

@app.get("/api/validWordleWord")
async def is_valid_word(word: str = Query(...)):
    global words
    if word.lower() in words:
        return {"isValid": True}
    return {"isValid": False}


@app.post("/api/trivia")
async def generate_question(request: MessageRequest):
    category = request.category
    message = "Generate me a random trivia question with the correct answer and 3 false answers, The Topic should be " + category + " and respond ONLY in json format as given here: {\"question\":\"\",\"answers\":[\"\",\"\", \"\", \"\"]} for the answers value it should be an array where the first index is the correct answer."
    response = requests.post(generate_api_url, json={"message": message})
    return parse_json_from_string(response.json()["response"])

@app.post("/api/generate")
async def gernerate(request: GenerateRequest):
    if request.key != api_key:
        return {"error": "Invalid API Key"}
    response = requests.post(generate_api_url, json={"message": request.message})
    return response.json()["response"]

@app.post("/api/note")
async def generate_note(request: GenerateNote):
    message = f"{generate_note_prompt}\nname: {request.student_name}; \nprevious note: {request.previous_note}; \nconcepts: {request.concepts}"
    response = requests.post(generate_api_url, json={"message": message})
    return response.json()["response"]

@app.get("/api/weather")
async def get_weather(city: str = Query(...)):
    try:
        geolocation_response = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={open_weather_key}")
        geolocation_data = geolocation_response.json()
        if not geolocation_data:
            return {"error": "geolocation api failed"}
        else:
            print(geolocation_data)

        lat = geolocation_data[0]["lat"]
        lon = geolocation_data[0]["lon"]

        weather_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={open_weather_key}")
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        return {"weather": weather_data["main"], "wind": weather_data["wind"], "misc": weather_data["weather"]}

    except Exception as e:
        print(e)
        return {"error":  "request failed"}


@app.get("/api/fact")
async def get_fact():
    try:
        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
        return {"fact": response.json()["text"]}
    except():
        return {"Error": "facts api error"}

UPLOAD_DIR = "/app/shared_files"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


@app.post("/api/upload")
async def upload_files(files: list[UploadFile]):
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
    return {"filenames": [file.filename for file in files]}


@app.get("/api/download")
def download_all_files():
    zip_filename = "all_files.zip"
    zip_filepath = os.path.join(UPLOAD_DIR, zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for root, _, files in os.walk(UPLOAD_DIR):
            for file in files:
                if file != zip_filename:  # Avoid zipping the zip file itself
                    zipf.write(os.path.join(root, file), file)

    return FileResponse(zip_filepath, filename=zip_filename)


@app.post("/api/clear")
def clear_files():
    for root, dirs, files in os.walk(UPLOAD_DIR):
        for file in files:
            os.remove(os.path.join(root, file))
    return JSONResponse(content={"message": "All files have been deleted."})