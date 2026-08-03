from groq import Groq
import streamlit as st

def get_groq_client():
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if not groq_key:
        return None
    return Groq(api_key=groq_key)

def generate_ai_response(client, api_messages):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=api_messages,
        temperature=0.2,
        max_tokens=1024,
    )
    return completion.choices[0].message.content
