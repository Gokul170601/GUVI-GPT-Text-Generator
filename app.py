# Import necessary libraries
import streamlit as st
import mysql.connector
import bcrypt
import datetime
import re
import pytz
import time

# Import transformers library for GPT-2 model
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch

# Configure Streamlit page settings
icon='https://media.istockphoto.com/id/1413286466/vector/chat-bot-icon-robot-virtual-assistant-bot-vector-illustration.jpg?s=612x612&w=0&k=20&c=ZSG3eqGPDJgIgFUIuVxID64uVUF3eqM3LrrDWtaKses='
st.set_page_config(page_title='GUVI - GPT',page_icon=icon, menu_items={"about":'This streamlit application was developed by M.Gokul'})

# Connect to TiDB Cloud database
mydb = mysql.connector.connect(
    host='host url', # Replace with your TiDB host URL
    port=4000,
    user='username', # Replace with your TiDB username
    password='password'  # Replace with your TiDB password
)
mycursor = mydb.cursor(buffered=True)

# Create 'GUVI_DB' database and use
mycursor.execute("CREATE DATABASE IF NOT EXISTS GUVI_DB")
mycursor.execute('USE GUVI_DB')

# Create 'users' table if it does not exist
mycursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    registered_date TIMESTAMP,
    last_login TIMESTAMP
);''')

# Check if username exists in the database
def username_exists(username):
    mycursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    return mycursor.fetchone() is not None

# Check if email exists in the database
def email_exists(email):
    mycursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    return mycursor.fetchone() is not None

# Validate email format using regular expressions
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Create a new user in the database
def create_user(username, password, email):
    if username_exists(username):
        return 'username_exists'
    
    if email_exists(email):
        return 'email_exists'
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    registered_date = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))

    # Insert user data into 'users' table
    mycursor.execute(
        "INSERT INTO users (username, password, email, registered_date) VALUES (%s, %s, %s, %s)",
        (username, hashed_password, email, registered_date)
    )
    mydb.commit()
    return 'success'

# Verify user credentials
def verify_user(username, password):
    mycursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    record = mycursor.fetchone()
    if record and bcrypt.checkpw(password.encode('utf-8'), record[0].encode('utf-8')):
        # Update last login timestamp
        mycursor.execute("UPDATE users SET last_login = %s WHERE username = %s", (datetime.datetime.now(pytz.timezone('Asia/Kolkata')), username))
        mydb.commit()
        return True
    return False

# Reset user password
def reset_password(username, new_password):
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    # Update password in 'users' table
    mycursor.execute(
        "UPDATE users SET password = %s WHERE username = %s",
        (hashed_password, username)
    )
    mydb.commit()

# Session state management
if 'sign_up_successful' not in st.session_state:
    st.session_state.sign_up_successful = False
if 'login_successful' not in st.session_state:
    st.session_state.login_successful = False
if 'reset_password' not in st.session_state:
    st.session_state.reset_password = False
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'


# Login form
def login():
    with st.form(key='login', clear_on_submit=True):
        st.subheader(':blue[**Login**]')
        st.write("Enter your username and password below.")
        
        # Input fields for username and password
        username = st.text_input(label='Username', placeholder='Enter Your Username')
        password = st.text_input(label='Password', placeholder='Enter Your Password', type='password')
        
        if st.form_submit_button('Login'):
            if not username or not password:
                st.error("Please fill out all fields.")
            elif verify_user(username, password):
                st.session_state.login_successful = True
                st.session_state.username = username
                st.session_state.current_page = 'home'
                st.rerun()
            else:
                st.error("Incorrect username or password. If you don't have an account, please sign up.")
                
    # Display sign-up and reset password button
    if not st.session_state.login_successful:
        c1, c2 = st.columns(2)
        with c1:
            st.write(":red[New user?]")
            if st.button('Sign Up'):
                st.session_state.current_page = 'sign_up'
                st.rerun()
        with c2:
            st.write(":red[Forgot Password?]")
            if st.button('Reset Password'):
                st.session_state.current_page = 'reset_password'
                st.rerun()


# Sign-up form
def signup(): 
    with st.form(key='signup', clear_on_submit=True):
        st.subheader(':blue[**Sign Up**]')
        st.write("Enter the required fields to create a new account.")

        # Input fields for email, username, and password
        email = st.text_input(label='Email', placeholder='Enter Your Email')
        username = st.text_input(label='Username', placeholder='Enter Your Username')
        password = st.text_input(label='Password', placeholder='Enter Your Password', type='password')
        re_password = st.text_input(label='Confirm Password', placeholder='Confirm Your Password', type='password')
        

        if st.form_submit_button('Sign Up'):
            if not email or not username or not password or not re_password:
                st.error("Please fill out all fields.")
            elif not is_valid_email(email):
                st.error("Please enter a valid email address.")
            elif len(password) <= 3:
                st.error("Password too short")
            elif password != re_password:
                st.error("Passwords do not match. Please re-enter.")
            else:
                result = create_user(username, password, email)
                if result == 'username_exists':
                    st.error("Username already registered. Please use a different username.")
                elif result == 'email_exists':
                    st.error("Email already registered. Please use a different email.")
                elif result == 'success':
                    st.success(f"Username {username} created successfully! Please login.")
                    st.session_state.sign_up_successful = True
                else:
                    st.error("Failed to create user. Please try again later.")

    if st.session_state.sign_up_successful:
        if st.button('Go to Login'):
            st.session_state.current_page = 'login'
            st.rerun()


# Reset password form
def reset_password_page():
    with st.form(key='reset_password', clear_on_submit=True):
        st.subheader(':blue[Reset Password]')
        st.write("Enter your username and new password below.")

        # Input fields for username and new password       
        username = st.text_input(label='Username', value='')
        new_password = st.text_input(label='New Password', type='password')
        re_password = st.text_input(label='Confirm New Password', type='password')

        if st.form_submit_button('Reset Password'):
            if not username:
                st.error("Please enter your username.")
            elif not username_exists(username):
                st.error("Username not found. Please enter a valid username.")
            elif not new_password or not re_password:
                st.error("Please fill out all fields.")
            elif len(new_password) <= 3:
                st.error("Password too short")
            elif new_password != re_password:
                st.error("Passwords do not match. Please re-enter.")
            else:
                reset_password(username, new_password)
                st.success("Password reset successfully. Please login with your new password.")
                st.session_state.current_page = 'login'

    # Button to return to login page
    st.write('Return to Login page')
    if st.button('Login'):
        st.session_state.current_page = 'login'
        st.rerun()



# HTML and CSS for the animated title and Disclaimer
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #0E1117;
            color: #ffffff;
        }
        .title {
            font-size: 3rem;
        }
        .animated {
            display: inline-block;
            background: linear-gradient(90deg, #ff5733, #33ff57, #3357ff, #ff33a1);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradient 8s ease infinite;
        }
        @keyframes gradient {
            0% {
                background-position: 0% 50%;
            }
            50% {
                background-position: 100% 50%;
            }
            100% {
                background-position: 0% 50%;
            }
        }
    </style>
</head>
<body>
    <h2 class="title">
        <span class="animated">GUVI GPT - Text Generator</span> 
    </h2>
</body>
</html>
"""


# CSS style for the running ticker effect
ticker_style = """
<style>
.ticker-wrap {
    overflow: hidden;
    position: relative;
    box-sizing: border-box;
    padding: 10px;
    background-color: #0E1117; 
    color: #FAFAFA; 
    font-size: 18px;
    white-space: nowrap;
}
.ticker-item {
    display: inline-block;
    padding-right: 30px; 
    animation: ticker-slide 15s linear infinite;
}
@keyframes ticker-slide {
    0% {
        transform: translateX(100%);
    }
    100% {
        transform: translateX(-100%);
    }
}
</style>
"""


img='https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExOGttcXJnNXZ5azl5bnNrbDk1bnZ4eTJkeWNtbGJhM2I4ZDZheWplMiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/5k5vZwRFZR5aZeniqb/giphy.webp'

disclaimer_message = "Disclaimer: Model data sourced from various web articles. Performance may vary based on data quality and relevance."



# Load the fine-tuned model and tokenizer
model_name_or_path = "./fine_tuned_model"
model = GPT2LMHeadModel.from_pretrained(model_name_or_path)
tokenizer = GPT2Tokenizer.from_pretrained(model_name_or_path)

# Set the pad_token to eos_token if it's not already set
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Move the model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)


# Define the text generation function
def generate_text(model, tokenizer, seed_text, max_length=100, temperature=0.01, num_return_sequences=1):
    # Tokenize the input text with padding
    inputs = tokenizer(seed_text, return_tensors='pt', padding=True, truncation=True)

    input_ids = inputs['input_ids'].to(device)
    attention_mask = inputs['attention_mask'].to(device)

    # Generate text
    with torch.no_grad():
        output = model.generate(
            input_ids,
            attention_mask=attention_mask,
            max_length=max_length,
            temperature=temperature,
            num_return_sequences=num_return_sequences,
            do_sample=True,
            top_k=50,
            top_p=0.1,
            pad_token_id=tokenizer.eos_token_id  # Ensure padding token is set to eos_token_id
        )

    # Decode the generated text
    
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)

    for word in generated_text.split():
        yield word + " "
        time.sleep(0.1)

        
#home page
def home_page():
    
    with st.sidebar:
        
        st.title(f"Welcome, {st.session_state.username}!")
        st.image(img,use_column_width=True)

        st.markdown('<br>',unsafe_allow_html=True)

        st.write("### Example Prompts")
        st.markdown(''' Guvi is an <br> Founders of guvi''',unsafe_allow_html=True)

        st.markdown('<br>',unsafe_allow_html=True)

        max=st.slider('Select MAX words',10,250)

        if st.button("Logout"):
            st.session_state.clear()
            st.session_state.current_page = 'login'
            st.rerun()



    # Display the animated title in Streamlit
    st.markdown(html_content, unsafe_allow_html=True)
    st.markdown(ticker_style, unsafe_allow_html=True)
    st.markdown(f'<div class="ticker-wrap"><div class="ticker-item">{disclaimer_message}</div></div>', unsafe_allow_html=True)


    if "messages" not in st.session_state:
        st.session_state.messages = []

    if prompt := st.chat_input("What up?"):
    
        with st.chat_message("user"):
            st.markdown(prompt)
    
            st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            
            response = st.write_stream(generate_text(model, tokenizer, seed_text=prompt, max_length=max, temperature=0.01, num_return_sequences=1))

            st.session_state.messages.append({"role": "assistant", "content": response})

        


# Display appropriate page based on session state
if st.session_state.current_page == 'home':
    home_page()
elif st.session_state.current_page == 'login':
    login()
elif st.session_state.current_page == 'sign_up':
    signup()
elif st.session_state.current_page == 'reset_password':
    reset_password_page()
