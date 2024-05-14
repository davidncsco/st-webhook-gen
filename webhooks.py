import streamlit as st
import requests
from requests import HTTPError
import os, time, random, copy
import pandas as pd

access_token = None
WEBEX_API_PREFIX = 'https://webexapis.com'

@st.cache_data
def fetch_all_rooms():
    """  Returns list of teams to which the authenticated user belongs and is moderator
    """
    url = WEBEX_API_PREFIX + "/v1/rooms"
    
    rooms = {}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        rooms_data = response.json()
        for room in rooms_data["items"]:
            rooms[room['title']] = room['id']
        return rooms
    else:
        print(f"Error fetching rooms. Status code: {response.status_code}")
        

def get_random_star_wars_character():
    # Fetch data from SWAPI, return a random character name, replacing space with underline
    response = requests.get("https://swapi.dev/api/people/")
    if response.status_code != 200:
        print("Error fetching data from SWAPI")
        return None

    characters = response.json().get("results", [])
    if not characters:
        print("No characters found in SWAPI data")
        return None
    # Select a random character and convert to lowercase, replace space with underline
    random_character = random.choice(characters).get("name","unknown").lower().replace(' ','_')
    return random_character

def get_unused_webhook(webhooks):
    match_found = True
    while match_found:
        characters = get_random_star_wars_character()
        match_found = any(webhook["hook"] == characters for webhook in webhooks)
    return characters

def fetch_webhooks(rooms):
    # Fetch all webhooks from DB
    
    response = requests.get(webhook_server_url)
    if response.status_code != 200:
        print("Error fetching webhooks from DB")
        return None
    return response.json()

def fetch_my_webhooks(rooms, webhooks):
    my_webhooks = []
    # Reverse key,value pair in rooms
    reversed_rooms =  {value: key for key, value in rooms.items()}
    for webhook in webhooks:
        room_title = reversed_rooms.get(webhook['roomId'])
        if room_title is not None:
            my_webhooks.append({'title':room_title,'hook': webhook['name'], 'template':webhook['template']})
    return my_webhooks
            
def rooms_without_webhooks(rooms,webhooks):
    new_rooms = copy.deepcopy(rooms)
    for webhook in webhooks:
        del new_rooms[webhook['title']]
    return new_rooms
    
def add_bot_to_room( room_id ):
    # Add bot membership to room so bot can send message to room when processing webhooks
    bot_email = st.secrets["bot_email"]
    # Build the request URL
    url = WEBEX_API_PREFIX + "/v1/memberships"

    # Prepare JSON data for the membership
    data = {"roomId": room_id, "personEmail": bot_email}
    # Send POST request
    response = requests.post(url, headers=headers, json=data)
    if response.status_code != 200:
        st.error(f"Error adding bot to room, status code = {response.status_code}")

    
def register_webhook(roomId, name, template):
    webhook_data = { 
                "roomId" : roomId,
                "name": name,
                "template": template }
    response = requests.post(webhook_server_url, json=webhook_data)
    if response.status_code != 200:
        st.error(f"Error creating webhooks, status code = {response.status_code}")
        return None
    # Add DevNet Community bot for Webhook to the room (commonroom@webex.bot)
    add_bot_to_room(roomId)
    st.success("Webhook registered")
    return response.json()


if __name__ == "__main__":
    
    # Input token variable either from sidebar or environment variable
    access_token = st.sidebar.text_input("Webex Access Token", os.getenv("WEBEX_ACCESS_TOKEN"))
    # Read webhooks server URL from secrets
    webhook_server_url = st.secrets["webhook_server_url"]
    col1, col2 = st.columns([1,2])
    col1.image('webhooks.jpg', caption='Webhooks Generator for Webex Rooms',width=220)
    
    if access_token == None:  # Must provide access token before continue
        st.write("Please provide your WEBEX access token before continue.")
        st.stop()
        
    headers = { 
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Fetch all rooms that this user is belonging to
    with st.spinner("Fetching all rooms..."):
        rooms = fetch_all_rooms()
    # Display generated webhook payload URL from DB
    webhooks = fetch_webhooks(rooms)
    my_webhooks = fetch_my_webhooks(rooms,webhooks)
    df = pd.DataFrame(my_webhooks)
    df = df.rename(columns={'title': 'Room Title', 'hook': 'Hook Name'})
    col2.dataframe(df, hide_index=True)
    col2.write(f"Webhook payload URL -> {webhook_server_url}process/<Hook Name>")
    template = st.radio('Select a message template for this Webex room',
                        [1, 2, 3])
    selected_room = st.selectbox("Please select a Webex room from list:", rooms_without_webhooks(rooms,my_webhooks))
    if selected_room:
        st.write("Press button to generate a random string as suffix for webhook payload URL")
        generate_button = st.button("Generate")
        if "generated_state" not in st.session_state:
            st.session_state.generated_state = False
        if generate_button or st.session_state.generated_state:
            characters = get_unused_webhook(my_webhooks)
            st.markdown(f"You selected: \"**{selected_room}**\" room, suffix generated: \":red[**{characters}**]\"")
            st.write(f"Room ID = {rooms[selected_room]}")
            st.write("Click on button to register your webhook")
            confirm_button = st.button("Register", on_click=register_webhook, args=(rooms[selected_room],characters,template))
        else:
            st.write("Please select a room then click generate.")

