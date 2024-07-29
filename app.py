from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os

app = Flask(__name__)
app.secret_key = 'f63e4ef09ab00ca7eb3519f3'

def load_users():
    with open('users.json') as f:
        return json.load(f)

def save_message(message, user):
    message_entry = {
        'user': user,
        'message': message
    }
    messages = []
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            messages = json.load(f)
    
    # Update the existing message if the user already has one
    found = False
    for entry in messages:
        if entry.get('user') == user:
            entry['message'] = message
            found = True
            break
    
    if not found:
        # Add a new entry if the user does not have one
        messages.append(message_entry)

    with open('data.json', 'w') as f:
        json.dump(messages, f, indent=4)

def load_user_message(user):
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            messages = json.load(f)
        for entry in messages:
            if entry.get('user') == user:
                return entry.get('message', "")
    return ""

def delete_user_message(user):
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            messages = json.load(f)
        messages = [entry for entry in messages if entry.get('user') != user]
        with open('data.json', 'w') as f:
            json.dump(messages, f, indent=4)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username]['password'] == password:
            session['user'] = username
            return redirect(url_for('message'))
        else:
            return 'Invalid credentials', 403
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
def message():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = session['user']
    if request.method == 'POST':
        message = request.form['message']
        save_message(message, user)
    
    user_message = load_user_message(user)
    return render_template('message.html', current_user=user, user_message=user_message)

@app.route('/delete', methods=['POST'])
def delete():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = session['user']
    delete_user_message(user)
    return redirect(url_for('message'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
