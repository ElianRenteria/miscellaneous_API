from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json, requests
from pydantic import BaseModel

app = FastAPI()

# Define the Pydantic model for the request body
class MessageRequest(BaseModel):
    category: str

class WeatherRequest(BaseModel):
    city: str

def parse_json_from_string(string_with_json):
    # Find where the JSON starts
    start_index = string_with_json.find('{')

    if (start_index == -1):
        raise ValueError("No JSON object found in the string")

    # Find where the JSON ends
    end_index = string_with_json.rfind('}') + 1

    if (end_index == 0):
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
    response = requests.post("http://elianrenteria.net:8000/generate", json={"message": "Generate me a random trivia question with the correct answer and 3 false answers and respond ONLY in json format as given here: {\"question\":\"\",\"answers\":[\"\",\"\", \"\", \"\"]} for the answers value it should be an array where the first index is the correct answer."})
    return parse_json_from_string(response.json()["response"])

@app.post("/api/trivia")
async def generate_question(request: MessageRequest):
    category = request.category
    message = "Generate me a random trivia question with the correct answer and 3 false answers, The Topic should be " + category + " and respond ONLY in json format as given here: {\"question\":\"\",\"answers\":[\"\",\"\", \"\", \"\"]} for the answers value it should be an array where the first index is the correct answer."
    response = requests.post("http://elianrenteria.net:8000/generate", json={"message": message})
    return parse_json_from_string(response.json()["response"])

@app.get("/api/weather")
async def get_weather(request: WeatherRequest):
    try:
        city = request.city
        geolocation = requests.get("http://api.openweathermap.org/geo/1.0/direct?q="+city+"&limit=1&appid=f50190f583ecbc5dc7d125322da65fbe")
        lat = geolocation.json()[0]["lat"]
        lon = geolocation.json()[0]["lon"]
        weather = requests.get("https://api.openweathermap.org/data/2.5/weather?lat="+str(lat)+"&lon="+str(lon)+"&appid=f50190f583ecbc5dc7d125322da65fbe")
        data = weather.json()
        return { "weather": data["main"], "wind": data["wind"], "misc": data["weather"] }
    except():
        return {"Error": "500"}

@app.get("/api/fact")
async def get_fact():
    try:
        response = requests.get("https://uselessfacts.jsph.pl/api/v2/facts/random?language=en")
        return {"fact":response.json()["text"]}
    except():
        return {"Error": "500"}