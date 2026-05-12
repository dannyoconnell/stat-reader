import os
import json
# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API client
# Assuming the user provides GEMINI_API_KEY in the .env file
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def extract_scoreboard(image_path, game_name):
    """
    Takes an image file path and a game name, sends it to Gemini,
    and returns a JSON string representing the scoreboard.
    """
    
    # Upload the file to Gemini to get a File object
    # Or we can just pass the PIL Image object directly to generate_content
    # pyrefly: ignore [missing-import]
    import PIL.Image
    img = PIL.Image.open(image_path)
    
    # Prompt engineering is critical here
    prompt = f"""
    You are an expert at analyzing video game post-game scoreboards.
    This is a screenshot of a {game_name} scoreboard.
    
    Please extract the player statistics from this scoreboard.
    Return ONLY a valid JSON array of objects. Do not include markdown code blocks like ```json ... ```. 
    Just the raw JSON array.
    
    Each object in the array should represent ONE player and have these exact keys based on the game:
    - "PlayerName": The player's name (string)
    
    And then include the relevant stats for {game_name}. 
    For example:
    - If Rocket League: "Score", "Goals", "Assists", "Saves", "Shots"
    - If Overwatch: "Eliminations", "Assists", "Deaths", "Damage", "Healing", "Mitigated"
    - If Valorant: "Kills", "Deaths", "Assists", "CombatScore"
    - If League of Legends: "Kills", "Deaths", "Assists", "CS", "Gold", "Damage"
    
    Ensure all numerical values are integers or floats, not strings.
    If a value is missing or unreadable, use null.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img]
        )
        
        # Clean up the response if Gemini returned markdown formatting
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        data = json.loads(text.strip())
        return data
        
    except Exception as e:
        print(f"Error extracting data: {e}")
        return None
