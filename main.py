from fastapi import FastAPI, Query, File, UploadFile, HTTPException, Form
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
import pandas as pd
from pathlib import Path
from typing import List
import pillow_heif
from io import BytesIO
import base64

load_dotenv()

open_weather_key = os.getenv('OPEN_WEATHER_KEY')
generate_api_url = os.getenv('GENERATE_API_URL')
whatbeats_api_url = os.getenv('WHATBEATS_API_URL')
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
class whatBeatsRequest(BaseModel):
    key: str
    current_object: str
    player_input:str

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
    "https://elianrenteria.dev",
    "76.176.106.64",
    "https://modern-spaniel-locally.ngrok-free.app"
]
#origins = ["*"]

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


@app.post("/api/whatbeats")
async def what_beats(request: whatBeatsRequest):
    if request.key == api_key:
        m = f"""You are an AI for a game called "What Beats Rock?" The game works as follows:
- The player submits an object that they believe can "beat" the current object.
- You must determine if their input is valid or invalid based on basic logic and reasoning.
- If valid, accept it and provide a short sentence creative or logical explanation for why it wins.
- If invalid, reject it and explain why in a short sentence.
- The accepted input becomes the new object for the next round.

Current object: {request.current_object}  
Player's input: {request.player_input}  

Respond in this format:
- **Validity:** "Accepted" or "Rejected"  
- **Explanation:** A short, fun, or logical reason why it beats or fails."  

Make sure responses are engaging, fun, and logical!
"""
        response = requests.post(whatbeats_api_url, json={"message": m})
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

# Specify the path to the CSV file
path = "./starbucks_drinks.csv"

# Load the CSV file into a DataFrame
data = pd.read_csv(path)
image_data = {
    "Brewed Coffee": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_DecafPikePlaceRoast.jpg?impolicy=1by1_wide_topcrop_630",
    "Caffè Latte": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_CaffeLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Caffè Mocha (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220607_CaffeMocha.jpg?impolicy=1by1_wide_topcrop_630",
    "Vanilla Latte (Or Other Flavoured Latte)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_CaffeLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Caffè Americano": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_CaffeAmericano.jpg?impolicy=1by1_wide_topcrop_630",
    "Cappuccino": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_Cappuccino.jpg?impolicy=1by1_wide_topcrop_630",
    "Espresso": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_Espresso_Single.jpg?impolicy=1by1_wide_topcrop_630",
    "Skinny Latte (Any Flavour)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_CaffeLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Caramel Macchiato": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20211029_CaramelMacchiato.jpg?impolicy=1by1_wide_topcrop_630",
    "White Chocolate Mocha (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_WhiteChocolateMocha.jpg?impolicy=1by1_wide_topcrop_630",
    "Hot Chocolate (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190617_SignatureHotChocolate.jpg?impolicy=1by1_wide_topcrop_630",
    "Caramel Apple Spice (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190624_CaramelAppleSpice.jpg?impolicy=1by1_wide_topcrop_630",
    "Tazo® Tea": "https://globalassets.starbucks.com/digitalassets/products/bev/ChaiBrewedTea.jpg?impolicy=1by1_wide_topcrop_630",
    "Tazo® Chai Tea Latte": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220411_ChaiLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Tazo® Green Tea Latte": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20211115_MatchaTeaLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Tazo® Full-Leaf Tea Latte": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190624_RoyalEnglishBreakfastTeaLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Tazo® Full-Leaf Red Tea Latte (Vanilla Rooibos)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220411_ChaiLatte.jpg?impolicy=1by1_wide_topcrop_630",
    "Iced Brewed Coffee (With Classic Syrup)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20210611_ColdBrew.jpg?impolicy=1by1_wide_topcrop_630",
    "Iced Brewed Coffee (With Milk & Classic Syrup)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20210611_ColdBrew.jpg?impolicy=1by1_wide_topcrop_630",
    "Shaken Iced Tazo® Tea (With Classic Syrup)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190531_IcedBlackTea.jpg?impolicy=1by1_wide_topcrop_630",
    "Shaken Iced Tazo® Tea Lemonade (With Classic Syrup)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190531_IcedBlackTeaLemonade.jpg?impolicy=1by1_wide_topcrop_630",
    "Banana Chocolate Smoothie": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220607_1509_PeppermintHotChocolate-onGreen-MOP_1800.jpg?impolicy=1by1_wide_topcrop_630",
    "Orange Mango Banana Smoothie": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20221216_FrozenPineapplePassionfruitRefresherLemonade.jpg?impolicy=1by1_wide_topcrop_630",
    "Strawberry Banana Smoothie": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20221216_FrozenStrawberryAcaiRefresherLemonade.jpg?impolicy=1by1_wide_topcrop_630",
    "Coffee": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190528_CoffeeFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Mocha (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190528_MochaFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Caramel (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220323_CaramelFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Java Chip (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190528_JavaChipFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Mocha": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190528_MochaFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Caramel": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220323_CaramelFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Java Chip": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20190528_JavaChipFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Strawberries & Crème (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20220323_StrawberryFrapp.jpg?impolicy=1by1_wide_topcrop_630",
    "Vanilla Bean (Without Whipped Cream)": "https://globalassets.starbucks.com/digitalassets/products/bev/SBX20181113_VanillaBeanFrapp.jpg?impolicy=1by1_wide_topcrop_630"
}

@app.get("/api/starbucks")
async def get_random_starbucks_drink():
    # Pick a new random row each time the endpoint is called
    random_row = data.sample(n=1)
    drink_data = json.loads(random_row.to_json(orient='records'))[0]
    return {"drink": drink_data, "image": image_data[drink_data["Beverage"]]}  # Use 'records' for better formatting

# Path to store the images
PHOTO_DIR = "./photos"
METADATA_FILE = os.path.join(PHOTO_DIR, "metadata.txt")

# Ensure the directory exists
os.makedirs(PHOTO_DIR, exist_ok=True)

# Helper function to read metadata
def read_metadata():
    metadata = {}
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as file:
            for line in file:
                parts = line.strip().split('|')
                if len(parts) == 3:
                    filename, note, date = parts
                    metadata[filename] = {"note": note, "date": date}
    return metadata

# Function to convert HEIC to JPEG
def convert_heic_to_jpeg(heic_path, jpeg_path):
    heif_file = pillow_heif.open_heif(heic_path)
    image = Image.frombytes(
        heif_file.mode, 
        heif_file.size, 
        heif_file.data
    )
    image.save(jpeg_path, "JPEG")

# Helper function to write metadata
def write_metadata(filename, note, date):
    with open(METADATA_FILE, "a") as file:
        file.write(f"{filename}|{note}|{date}\n")
        
def delete_image(filename):
    metadata = read_metadata()
    
    # Check if the image exists in metadata
    if filename not in metadata:
        raise HTTPException(status_code=404, detail="Image not found in metadata")

    # Remove the image file if it exists
    file_path = os.path.join(PHOTO_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Rewrite metadata.txt without the deleted entry
    with open(METADATA_FILE, "w") as file:
        for img, data in metadata.items():
            if img != filename:  # Keep other entries
                file.write(f"{img}|{data['note']}|{data['date']}\n")

    return {"message": "Image deleted successfully"}

# FastAPI Endpoint
@app.delete("/api/delete_image/{filename}")
async def delete_image_endpoint(filename: str):
    return delete_image(filename)


# Upload endpoint with HEIC conversion
@app.post("/api/upload_image")
async def upload_image(note: str = Form(...), date: str = Form(...), file: UploadFile = File(...)):
    original_filename = file.filename
    file_extension = original_filename.lower().split('.')[-1]

    # Define file path for saving
    file_path = os.path.join(PHOTO_DIR, original_filename)

    # Save the uploaded file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Convert HEIC files
    if file_extension == "heic":
        jpeg_filename = original_filename.rsplit(".", 1)[0] + ".jpg"
        jpeg_path = os.path.join(PHOTO_DIR, jpeg_filename)

        try:
            convert_heic_to_jpeg(file_path, jpeg_path)
            os.remove(file_path)  # Remove original HEIC file after conversion
            final_filename = jpeg_filename
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"HEIC conversion failed: {str(e)}")
    else:
        final_filename = original_filename  # Keep original name for non-HEIC files

    # Store metadata
    write_metadata(final_filename, note, date)

    return {"filename": final_filename, "note": note, "upload_date": date}

# **New Endpoint: Get all images as Base64 with metadata**
@app.get("/api/images")
async def get_all_images():
    metadata = read_metadata()
    images = []

    for filename, data in metadata.items():
        file_path = os.path.join(PHOTO_DIR, filename)
        
        if os.path.exists(file_path):
            # Read image and encode as Base64
            with open(file_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")

            images.append({
                "image": f"data:image/jpeg;base64,{base64_image}",  # Data URL format
                "note": data["note"],
                "date": data["date"],
                "filename": filename
            })

    return {"images": images}

# Serve image files individually
@app.get("/api/images/file/{image_name}")
async def get_image_file(image_name: str):
    file_path = os.path.join(PHOTO_DIR, image_name)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image file not found")
