from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

app = Flask(__name__)

# Path to the Excel file
EXCEL_FILE = 'users.xlsx'

@app.route('/')
def home_page():
    return render_template('home.html')

# Route to render the signup page
@app.route('/signup')
def signup_form():
    return render_template('signup.html')

# Route to render the login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None  # Initialize message variable

    if request.method == 'POST':
        username = request.form['uname']
        password = request.form['pass']

        # Check if the Excel file exists
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)

            # Check if the username exists
            user = df[df['username'] == username]
            if user.empty:
                message = "Account doesn't exist"
            else:
                # Check if the password matches
                if user['password'].values[0] != password:
                    message = "Invalid username or password"
                else:
                    return redirect(url_for('account'))  # Redirect to account page if login is successful
        else:
            message = "No registered users found."

    return render_template('login.html', message=message)

# Route to render the account page
@app.route('/account')
def account():
    return render_template('account.html')

if __name__ == '__main__':
    app.run(debug=True)