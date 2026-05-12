import streamlit as st
import pandas as pd
import os
import json
from extractor import extract_scoreboard
from sheets import upload_stats, get_worksheet_names
from dotenv import load_dotenv

# Load environment variables
# Load environment variables (for local development)
load_dotenv()

# Ensure Streamlit secrets are pushed to os.environ for our backend scripts (for cloud deployment)
try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ[key] = value
except Exception:
    pass

st.set_page_config(page_title="Broadcast Stat Reader", page_icon="📊", layout="wide")

st.title("🎮 Broadcast Stat Reader")
st.write("Upload a post-game scoreboard screenshot to extract player stats and save them to Google Sheets.")

# Setup validation
if not os.environ.get("GEMINI_API_KEY"):
    st.warning("⚠️ GEMINI_API_KEY is not set in your environment or secrets. Image extraction will not work.")
    
# Check for either the JSON string (Cloud) OR the file path (Local)
has_json_str = bool(os.environ.get("GOOGLE_CREDENTIALS_JSON"))
has_file_path = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")))

if not has_json_str and not has_file_path:
    st.warning("⚠️ Neither GOOGLE_CREDENTIALS_JSON nor a valid GOOGLE_APPLICATION_CREDENTIALS file were found. Sheets upload will fail.")

# Sidebar for Configuration
st.sidebar.header("Configuration")
sheet_url = st.sidebar.text_input("Google Sheet URL or ID", 
                                  help="Paste the full URL of your Google Sheet or its ID here.")

# Main app layout
game_name = st.selectbox("Select Game", 
                         ["Rocket League", "Overwatch", "Valorant", "League of Legends"])

st.sidebar.divider()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_tabs(url):
    return get_worksheet_names(url)

worksheet_name = game_name

if sheet_url:
    with st.sidebar:
        with st.spinner("Fetching tabs from Google Sheets..."):
            tabs = fetch_tabs(sheet_url)
            
        if tabs:
            default_index = tabs.index(game_name) if game_name in tabs else 0
            worksheet_name = st.selectbox("Select Worksheet (Tab)", options=tabs, index=default_index,
                                          help="The specific tab in your Google Sheet where stats should be deposited.")
        else:
            st.warning("Could not fetch tabs. Is the Sheet shared with the Service Account?")
            worksheet_name = st.text_input("Worksheet (Tab) Name", value=game_name)
else:
    st.sidebar.info("Enter a Google Sheet URL above to select from available tabs.")

uploaded_file = st.file_uploader("Upload Scoreboard Screenshot", type=["png", "jpg", "jpeg", "webp"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Scoreboard", use_container_width=True)
    
    if st.button("Extract Stats", type="primary"):
        with st.spinner("Extracting stats using Gemini Vision..."):
            # Save the uploaded file temporarily
            temp_path = "temp_image.png"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            try:
                # Call the extractor
                extracted_data = extract_scoreboard(temp_path, game_name)
                
                if extracted_data:
                    # Store data in session state so it persists
                    st.session_state['extracted_data'] = extracted_data
                    st.success("Extraction successful!")
                else:
                    st.error("Failed to extract data. Please try again.")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

# If we have extracted data, show it and allow player selection
if 'extracted_data' in st.session_state and st.session_state['extracted_data']:
    st.divider()
    st.header("Extracted Stats")
    
    data = st.session_state['extracted_data']
    
    # Display the data as a table
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    # Get list of player names
    player_names = df['PlayerName'].tolist() if 'PlayerName' in df.columns else []
    
    if player_names:
        st.subheader("Record Stats to Sheets")
        
        selected_player = st.selectbox("Select a Player to Record", player_names)
        
        if st.button("Upload to Google Sheets", type="primary"):
            if not sheet_url:
                st.error("Please enter a Google Sheet URL in the sidebar.")
            else:
                with st.spinner("Uploading to Google Sheets..."):
                    # Find the player's stats
                    player_stats = next((item for item in data if item.get('PlayerName') == selected_player), None)
                    
                    if player_stats:
                        try:
                            upload_stats(game_name, selected_player, player_stats, sheet_url, worksheet_name)
                            st.success(f"Successfully uploaded stats for {selected_player} to Google Sheets!")
                        except Exception as e:
                            st.error(f"Failed to upload: {e}")
                            st.info("Make sure you have shared your Google Sheet with the Service Account email.")
                    else:
                        st.error("Could not find stats for the selected player.")
    else:
        st.warning("No 'PlayerName' column found in the extracted data. Check the AI prompt.")
