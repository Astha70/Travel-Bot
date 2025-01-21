import streamlit as st
import google.generativeai as genai
import os
import requests
import re
from dotenv import load_dotenv

load_dotenv()
GEM_API_KEY = st.secrets["GEM_API_KEY"]
genai.configure(api_key=GEM_API_KEY)

# Unsplash API setup
UNSPLASH_KEY = st.secrets["UNSPLASH_KEY"]
UNSPLASH_BASE_URL = "https://api.unsplash.com/search/photos"

def clean_heading(heading):
    """
    Cleans up the heading by removing unnecessary characters like 'A)', 'B)', '**', and other markdown syntax.
    
    Args:
        heading: The original heading string (e.g., "A) **Banff National Park**").
    
    Returns:
        A cleaned-up heading string (e.g., "Banff National Park").
    """
    heading_clean = re.sub(r"^[A-D]\)\s*\*\*|\*\*\s*$", "", heading)  # Remove the 'A)' part and surrounding '**'
    heading_clean = re.sub(r"\*\*", "", heading_clean)  # Remove any remaining '**' markdown
    
    # Further clean-up to trim spaces (optional)
    heading_clean = heading_clean.strip()
    
    return heading_clean

def get_unsplash_image(query):
    """
    Fetches a random image from Unsplash based on the query.
    
    Args:
        query: The search term (e.g., "beach", "mountain", etc.)
    
    Returns:
        Image URL from Unsplash or a default image if no result found.
    """
    
    try:
        params = {
            "query": query,
            "client_id": UNSPLASH_API_KEY,  # Unsplash API key
            "orientation": "landscape",     # Landscape orientation for travel images
            "count": 1                      # Get 1 image
        }
        response = requests.get(UNSPLASH_BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        if data:
            return data['results'][0]["urls"]["regular"]  # Return the URL of the image
    except Exception as e:
        st.error(f"Error fetching image from Unsplash: {e}")

    # Fallback image URL if no result is found or error occurs
    return "https://example.com/default_image.jpg"

def get_completion_from_messages(messages_gem, model="gemini-1.5-flash", temperature=0.1):
    contents = []
    system_prompt = ""

    for message in messages_gem:
        if message["role"] == "system":
            system_prompt = message["content"]
        elif message["role"] == "user":
            contents.append({"role": "user", "parts": [message["content"]]})
        elif message["role"] == "assistant":
            contents.append({"role": "model", "parts": [message["content"]]})

    if not contents and system_prompt:
        contents.append({"role": "user", "parts": [f"*{system_prompt}*"]})
    elif system_prompt:
        contents[0]["parts"].insert(0, f"*{system_prompt}*")

    try:
        response = genai.GenerativeModel(model).generate_content(
            contents=contents,
            generation_config=genai.GenerationConfig(max_output_tokens=1000, temperature=temperature),
        )
    except Exception as e:
        st.error(f"An error occurred while processing your request: {e}")
        return "An error occurred while processing your request."

    return response.text

def display_options(options, title="Choose an option:"):
    """
    Displays a list of options in a user-friendly format.

    Args:
        options: A list of options to display.
        title: The title for the options.

    Returns:
        None
    """
    st.write(title)
    for i, option in enumerate(options):
        if isinstance(option, tuple):  # Handle tuples (place, description)
            st.markdown(f"**{i+1}. {option[0]}**\n")  # Bold heading with line break
        else:
            st.markdown(f"{option}\n")  # Each activity on a new line


def extract_recommendations(response_text):
    recommendations = []

    for line in response_text.split("\n"):
        if line.startswith("A)") or line.startswith("B)") or line.startswith("C)") or line.startswith("D)"):
            parts = line.split(":** ")
            if len(parts) == 2:
                heading = parts[0].strip()
                # Clean up the heading to remove any unwanted characters
                cleaned_head = clean_heading(heading)
                # print(heading)
                description = parts[1].strip()
                recommendations.append((cleaned_head, description))

    return recommendations

def display_recommendation_cards(recommendations):
    """
    Display recommendations with images on cards.
    
    Args:
        recommendations: List of tuples where each tuple is (heading, description).
    """
    num_columns = 3
    cols = st.columns(num_columns, border=True)

    for i, (heading, description) in enumerate(recommendations):
        # Determine which column to display the current recommendation in
        col = cols[i % num_columns]

        with col:
            # Fetch the image for the heading
            image_url = get_unsplash_image(heading)

            # Display the recommendation as a card with heading, image, and description
            st.markdown(f"### {heading}")
            st.image(image_url, caption=heading, use_container_width=True)
            st.write(f"{description}\n")

def create_travel_bot():
    st.title("WanderWise: Your Travel Planner")

    if 'context' not in st.session_state:
        st.session_state.context = [
            {"role": "system", "content": """
                You are **WanderWise**, an automated travel assistant designed to help users craft unique and personalized travel experiences. 
                Your goal is to guide users through the process of planning their trips by offering destination suggestions and asking relevant questions to customize their journey.

                1. Greet the user and ask for their desired travel destination.
                2. Inquire if they prefer a popular tourist destination or something more off the beaten path. 
                3. Based on their answer, provide a curated list of options that suit their preference.
                4. After they select a destination, ask about desired activities, suggesting relevant options based on the chosen location.
                5. Summarize the entire trip plan, including destination and activities.
                
                Keep the conversation simple, helpful, and engaging while focusing on providing personalized suggestions. 
                When providing suggestions, please format them in a clear and concise manner, 
                such as:
                A) Heading: Description \n
                B) Heading: Description \n
                C) Heading: Description \n

                This will help users easily understand and select their preferred options.
                Do not ask for other aspects of trip like accommodation or transportation, just follow the steps.
            """}
        ]

    user_input = st.chat_input("Where would you love to go for your next adventure?")

    if user_input:
        st.session_state.context.append({"role": "user", "content": user_input})
        bot_reply = get_completion_from_messages(st.session_state.context)
        st.session_state.context.append({"role": "assistant", "content": bot_reply})
        st.write(f"**WanderWise:** {bot_reply}")

        if "tourist" in bot_reply.lower() and "or" in bot_reply.lower() and "path" in bot_reply.lower():
            display_options([("Tourist Spot", ""), ("Off the Beaten Path", "")], "Choose your preference:")
        
        if "A)" in bot_reply or "B)" in bot_reply or "C)" in bot_reply:
            recommendations = extract_recommendations(bot_reply)
            if recommendations:
                display_recommendation_cards(recommendations)

if __name__ == "__main__":
    create_travel_bot()
