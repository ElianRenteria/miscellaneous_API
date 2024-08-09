from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from pydantic import BaseModel
from dotenv import load_dotenv
import os, random

load_dotenv()

open_weather_key = os.getenv('OPEN_WEATHER_KEY')
generate_api_url = os.getenv('GENERATE_API_URL')

app = FastAPI()

with open('./data/wordle-words.txt', 'r') as file:
    words = file.readlines()
words = [word.strip() for word in words]

# Define the Pydantic model for the request body
class MessageRequest(BaseModel):
    category: str

class WeatherRequest(BaseModel):
    city: str

class ValidWordleRequest(BaseModel):
    word: str
      

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


# Add CORS middleware
origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://coderlab.work"
    # Add other origins as needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api")
async def root():
    return {"message": "Hello World"}


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
async def is_valid_word(request: ValidWordleRequest):
    global words
    if request.word in words:
        return {"isValid": True}
    return {"isValid": False}


@app.post("/api/trivia")
async def generate_question(request: MessageRequest):
    category = request.category
    message = "Generate me a random trivia question with the correct answer and 3 false answers, The Topic should be " + category + " and respond ONLY in json format as given here: {\"question\":\"\",\"answers\":[\"\",\"\", \"\", \"\"]} for the answers value it should be an array where the first index is the correct answer."
    response = requests.post(generate_api_url, json={"message": message})
    return parse_json_from_string(response.json()["response"])


@app.get("/api/weather")
async def get_weather(city: str):
    try:
        # Fetch geolocation data
        geolocation_response = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={open_weather_key}")
        geolocation_data = geolocation_response.json()
        if not geolocation_data:
            return {"error": "geolocation api failed"}
        else:
            print(geolocation_data)

        lat = geolocation_data[0]["lat"]
        lon = geolocation_data[0]["lon"]

        # Fetch weather data
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
