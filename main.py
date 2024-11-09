from fastapi import FastAPI, Query, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import requests
from pydantic import BaseModel
from dotenv import load_dotenv
import os, random, io, csv
import shutil
import zipfile
from rembg import remove
from PIL import Image
from tempfile import NamedTemporaryFile
import shutil
from random import randint

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
    
class LCDMessageRequest(BaseModel):
    message: str

class WeatherRequest(BaseModel):
    city: str

class GenerateRequest(BaseModel):
    message: str
    key: str

class GenerateNote(BaseModel):
    student_name: str
    previous_note: str
    concepts: str
    key:str

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
    "https://elianrenteria.github.io",
    "coderschoolpi.local",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the states from the CSV file into a list
def load_states():
    states = []
    with open("states.csv", "r") as file:
        reader = csv.reader(file)
        for row in reader:
            states.append(row[0])  # Assuming each state is in the first column
    return states

# Initialize the list of states
states = load_states()

@app.get("/api/state")
async def pick_state():
    random_state = random.choice(states)
    return {"state": random_state}

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
    response = requests.post(generate_api_url, json={"message": message, "key": api_key})
    return parse_json_from_string(response.json()["response"])

@app.post("/api/generate")
async def gernerate(request: GenerateRequest):
    if request.key == api_key:
        response = requests.post(generate_api_url, json={"message": request.message})
        return response.json()["response"]
    return {"error": "Invalid API Key"}

@app.post("/api/note")
async def generate_note(request: GenerateNote):
    message = f"{generate_note_prompt}\nname: {request.student_name}; \nprevious note: {request.previous_note}; \nconcepts: {request.concepts}"
    response = requests.post(generate_api_url, json={"message": message, "key": request.key})
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
async def upload_files(files: list[UploadFile] = File(...)):
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
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


@app.post("/api/remove-bg")
async def remove_bg(image: UploadFile = File(...)):
    contents = await image.read()
    input_image = Image.open(io.BytesIO(contents))

    # Remove the background
    output_image = remove(input_image)

    # Save the output image to a temporary file
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        output_image.save(tmp, format="PNG")
        tmp_path = tmp.name

    # Return the image as a file response
    return FileResponse(tmp_path, media_type="image/png", filename="processed-image.png")

POKE_API_BASE_URL = "https://pokeapi.co/api/v2/pokemon/"

@app.get("/api/pokemon")
async def get_random_pokemon():
    variables = {
        "id": randint(1, 1025)
    }

    URL = "https://beta.pokeapi.co/graphql/v1beta"
    query = """
    query samplePokeAPIquery($id: Int!) {
      pokemon_v2_pokemon(where: {id: {_eq: $id}}) {
        name
        pokemon_v2_pokemonsprites {
          sprites(path: "front_default")
        }
      }
    }
    """
    response = requests.post(URL, json={"query": query, "variables": variables}).json()
    payload = {
        "name": response["data"]["pokemon_v2_pokemon"][0]["name"],
        "image": response["data"]["pokemon_v2_pokemon"][0]["pokemon_v2_pokemonsprites"][0]["sprites"]
    }
    return payload
    '''
    # Total number of Pokémon in the API (you could make this dynamic if necessary)
    max_pokemon_id = 1025  # As of Gen 9

    # Generate a random Pokémon ID
    random_id = random.randint(1, max_pokemon_id)

    # Fetch Pokémon data from PokéAPI
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{POKE_API_BASE_URL}{random_id}/")

    if response.status_code == 200:
        data = response.json()
        pokemon_name = data['name']
        pokemon_image = data['sprites']['front_default']

        # Return the Pokémon name and image
        return {
            "name": pokemon_name,
            "image": pokemon_image
        }
    else:
        return {"error": "Failed to fetch data from PokeAPI"}
    '''

LCDMessage = ""

@app.post("/api/set_message")
async def set_message(request: LCDMessageRequest):
    if len(request.message) > 16:
        return {"error": "Message is too long. Max 16 characters allowed."}
    else:
        global LCDMessage
        LCDMessage = request.message
        return {"message": LCDMessage}
    
@app.get("/api/get_message")
async def get_message():
    global LCDMessage
    return {"message": LCDMessage}