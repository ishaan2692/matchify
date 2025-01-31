import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import hashlib

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    st.error("Google API Key not found. Please check your environment variables.")

# Helper function for caching extracted text per file (to prevent redundant processing)
def hash_pdf(uploaded_file):
    # Generate a hash to identify the unique file (this ensures caching works effectively)
    md5_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
    return md5_hash

@st.cache_data
def extract_text_from_pdf(uploaded_file):
    try:
        # Calculate file hash for caching
        file_hash = hash_pdf(uploaded_file)
        
        pdf_reader = PdfReader(uploaded_file)
        text_lines = [page.extract_text() for page in pdf_reader.pages]
        return "".join(text_lines), file_hash
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None, None

# Cache the generative model to avoid reloading it for each request
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def generate_text(uploaded_files, job_description):
    combined_pdf_text = ""
    file_hashes = []

    # Process each uploaded file and combine text
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            pdf_text, file_hash = extract_text_from_pdf(uploaded_file)
            if pdf_text:
                combined_pdf_text += pdf_text + "\n\n"
                file_hashes.append(file_hash)
    
    # If combined text exists, proceed with analysis
    if combined_pdf_text:
        # Directly display the extracted text without additional labels
        st.text_area("Extracted Text", combined_pdf_text, height=300)

        prompt = (
            "Assess candidate fit for the job description. Consider substitutes for skills, experience, match percentage in tabular form:\n\n"
            "Skills: Match or equivalent technologies.\n"
            "Experience: Relevance to key responsibilities.\n"
            "Fit: Suitability based on experience and skills.\n\n"
            f"Job Description:\n{job_description}\n\nResume Content:\n{combined_pdf_text}"
        )

        with st.spinner('Generating...'):
            response = model.generate_content([prompt], stream=True)
            response.resolve()
            st.markdown(response.text)

# Function to handle chatbot conversation with memory caching
def chatbot(user_input):
    # Initialize conversation history if it doesn't exist
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

    # Add user input to the conversation history
    st.session_state.conversation_history.append({"role": "User", "message": user_input})

    # Build conversation context from history
    conversation_context = "\n".join([f"{entry['role']}: {entry['message']}" for entry in st.session_state.conversation_history])
    prompt = f"{conversation_context}\nBot:"

    try:
        with st.spinner('Your virtual assistant is thinking...'):
            response = model.generate_content([prompt], stream=True)
            response.resolve()
            bot_response = response.text.strip()

            # Add bot's response to the conversation history
            st.session_state.conversation_history.append({"role": "Bot", "message": bot_response})
            return bot_response
    except Exception as e:
        st.error(f"Error with chatbot: {e}")
        return "Sorry, I couldn't process that request."

# Streamlit page configuration
st.set_page_config(page_title="PDF and Job Description Analysis App")

# Sidebar for navigation
st.sidebar.header("Navigation")
selected_page = st.sidebar.selectbox("Select a page", [
    "Home",
    "Job Description Analysis",
    "virtual assistant",
])

if selected_page == "Home":
    st.title("Welcome to Matchify!")
    st.write('"Connecting opportunities with the perfect fit."')
    st.write("Matchify is your go-to tool for seamlessly matching job descriptions with relevant PDF documents. "
             "Simply upload your job descriptions and PDF resumes, and let Matchify do the work. "
             "Our advanced text analysis and similarity matching technology will help you find the best candidates "
             "for your job openings, making the hiring process more efficient and effective.")
    st.title("Created by Ishaan.")
    #st.markdown('<p style="background-color: yellow; font-size: 20px;">Created by Ishaan.</p>', unsafe_allow_html=True)
    st.write("Connect with me on:")
    st.markdown("[GitHub](https://github.com/ishaan2692)")
    st.markdown("[LinkedIn](https://in.linkedin.com/in/ishaanbagul)")

elif selected_page == "Job Description Analysis":
    st.header("Job Description Analysis")
    
    # Allow multiple PDFs to be uploaded
    uploaded_files = st.file_uploader("Choose PDF files...", type=["pdf"], accept_multiple_files=True)
    
    job_description = st.text_area("Job Description", "")

    if st.button('Analyze'):
        if uploaded_files:
            generate_text(uploaded_files, job_description)
        else:
            st.error("Please upload at least one PDF file.")

elif selected_page == "virtual assistant":
    st.header("virtual assistant")
    user_input = st.text_input("Enter your message:")

    if user_input:
        bot_response = chatbot(user_input)
        st.write("Chatbot:", bot_response)

    # Display chat history with styled conversation bubbles
    if 'conversation_history' in st.session_state:
        st.write("### Conversation History")
        chat_box = st.empty()  # Empty container to display chat

        # Create a scrollable container for the conversation
        with chat_box.container():
            for entry in st.session_state.conversation_history:
                if entry["role"] == "User":
                    st.markdown(f'<div style="background-color: #D1E7FD; border-radius: 10px; padding: 10px; margin-bottom: 5px;">'
                                f'<b>User:</b> {entry["message"]}</div>', unsafe_allow_html=True)
                else:  # Bot
                    st.markdown(f'<div style="background-color: #E2F8D7; border-radius: 10px; padding: 10px; margin-bottom: 5px;">'
                                f'<b>Bot:</b> {entry["message"]}</div>', unsafe_allow_html=True)
