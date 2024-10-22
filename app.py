from flask import Flask, request, redirect, render_template, session, flash
from datetime import datetime, timedelta
import json
import os
import sendgrid
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')  # Use the SECRET_KEY environment variable

DATA_FILE = 'urls.json'
USERS_FILE = 'users.json'

# Load existing URLs
def load_urls():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

# Save URLs to a JSON file
def save_urls(url_mapping):
    with open(DATA_FILE, 'w') as file:
        json.dump(url_mapping, file)

# Load existing users
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}

# Save users to a JSON file
def save_users(user_mapping):
    with open(USERS_FILE, 'w') as file:
        json.dump(user_mapping, file)

# Email sending function
def send_email(subject, body, to_email):
    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDAPI'))
    message = Mail(
        from_email=os.environ.get('SENDEMAIL'),
        to_emails=to_email,
        subject=subject,
        plain_text_content=body
    )
    response = sg.send(message)
    return response

# URL mapping storage
url_mapping = load_urls()
user_mapping = load_users()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shorten', methods=['POST'])
def shorten():
    if 'username' not in session:
        flash("You must be logged in to shorten URLs.")
        return redirect('/login')
    
    original_url = request.form['url'].strip()
    keyword = request.form['keyword'].strip()

    # Add http if missing
    if not (original_url.startswith("http://") or original_url.startswith("https://")):
        original_url = "http://" + original_url

    # Validate the URL (basic check)
    if keyword in url_mapping:
        flash("Keyword already exists. Choose another one.")
        return redirect('/')

    # Set expiration date to 4 months from now
    expiration_date = (datetime.now() + timedelta(days=120)).isoformat()

    url_mapping[keyword] = {
        'original_url': original_url,
        'expiration_date': expiration_date,
        'username': session['username']
    }
    save_urls(url_mapping)

    return render_template('index.html', short_url=f"http://127.0.0.1:5000/{keyword}")

@app.route('/<keyword>')
def redirect_to_url(keyword):
    entry = url_mapping.get(keyword)
    if entry:
        expiration_date = datetime.fromisoformat(entry['expiration_date'])
        if datetime.now() < expiration_date:
            return redirect(entry['original_url'])  # Redirect to the actual URL
        else:
            return "This link has expired.", 404
    return "URL not found.", 404

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Prepare email content
        subject = "New Contact Form Submission"
        email_body = f"Name: {name}\nEmail: {email}\nMessage: {message}"

        # Send email
        try:
            send_email(subject, email_body, os.environ.get('SENDEMAIL'))  # Send to the specified email
            flash("Your message has been sent! We'll get back to you soon.")
        except Exception as e:
            flash(f"Failed to send message: {str(e)}")

        return redirect('/contact')

    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in user_mapping:
            flash("Username already exists. Please choose another.")
        else:
            user_mapping[username] = password
            save_users(user_mapping)
            flash("Registration successful! You can now log in.")
            return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if user_mapping.get(username) == password:
            session['username'] = username
            return redirect('/dashboard')
        else:
            flash("Invalid username or password.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash("You must be logged in to view your dashboard.")
        return redirect('/login')
    
    user_links = {k: v for k, v in url_mapping.items() if v.get('username') == session['username']}
    return render_template('dashboard.html', links=user_links)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("You have been logged out.")
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 6867))  # Use the PORT environment variable or default to 6867
    app.run(host='0.0.0.0', port=port, debug=True)
