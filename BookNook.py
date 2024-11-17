from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for sessions

USER_FILE = 'users.xlsx'
BOOK_FILE = 'books.xlsx'
PROFILE_PIC_FOLDER = 'static/profile_pics'
BOOK_COVER_FOLDER = 'static/book_covers'
USER_DB_FOLDER = 'user_databases'
os.makedirs(PROFILE_PIC_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist
os.makedirs(BOOK_COVER_FOLDER, exist_ok=True)
os.makedirs(USER_DB_FOLDER, exist_ok=True)

@app.route('/')
def home_page():
    return render_template('home.html', logged_in=session.get('logged_in'))

@app.route('/signup', methods=['GET', 'POST'])
def signup_form():
    if request.method == 'POST':
        # Handle profile picture upload
        profile_pic = request.files['propic']
        if profile_pic:
            pic_filename = profile_pic.filename
            profile_pic_path = f"profile_pics/{pic_filename}"
            profile_pic.save(os.path.join(PROFILE_PIC_FOLDER, pic_filename))

        # Gather other form data
        username = request.form['uname']
        password = request.form['pass']
        surname = request.form['surname']
        forename = request.form['forename']
        email = request.form['email']
        birth = request.form['birth']

        # Load or create the main user DataFrame
        if os.path.exists(USER_FILE):
            df = pd.read_excel(USER_FILE)
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
            new_id = df['ID'].max() + 1
        else:
            df = pd.DataFrame(columns=['ID', 'username', 'password', 'surname', 'forename', 'email', 'birth', 'profile_pic'])
            new_id = 1

        # Check if username already exists
        if not df[df['username'] == username].empty:
            message = "Username already exists"
            return render_template('signup.html', message=message)

        # Add new user to main user DataFrame
        new_user = pd.DataFrame([{
            'ID': new_id,
            'username': username,
            'password': password,
            'surname': surname,
            'forename': forename,
            'email': email,
            'birth': birth,
            'profile_pic': profile_pic_path
        }])
        df = pd.concat([df, new_user], ignore_index=True)
        df.to_excel(USER_FILE, index=False)

        # Create the user's personal database
        user_data = pd.DataFrame([{
            'username': username,
            'ID': new_id,  # Ensure the ID matches the one from users.xlsx
            'followers': [],  # Followers list (empty initially)
            'following': []   # Following list (empty initially)
        }])

        # Save the user's database to a file named <username>.xlsx
        user_data_file = os.path.join(USER_DB_FOLDER, f"{username}.xlsx")
        user_data.to_excel(user_data_file, index=False)

        # Set session login status and redirect to account page
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('account', username=username))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    if request.method == 'POST':
        username = request.form['uname']
        password = request.form['pass']

        if os.path.exists(USER_FILE):
            df = pd.read_excel(USER_FILE)
            user = df[df['username'] == username]

            if user.empty:
                message = "Account doesn't exist"
            elif user['password'].values[0] != password:
                message = "The password is incorrect"
            else:
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('account', username=username))
        else:
            message = "No registered users found."

    return render_template('login.html', message=message)

@app.route('/account/<username>')
def account(username):
    # Load user data from file
    if not os.path.exists(USER_FILE):
        return "User database not found", 404

    df = pd.read_excel(USER_FILE)
    user = df[df['username'] == username]

    if user.empty:
        return "User not found", 404

    user_info = user.iloc[0].to_dict()  # Get user data as a dictionary
    

    return render_template('account.html', user_info=user_info)

@app.route('/addbook', methods=['GET', 'POST'])
def add_book():
    # Redirect to login page if user is not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Handle book cover upload
        book_cover = request.files['bookcover']
        if book_cover:
            cover_filename = book_cover.filename
            book_cover_path = os.path.join(BOOK_COVER_FOLDER, cover_filename)
            book_cover.save(book_cover_path)

        # Gather other form data
        title = request.form['title']
        author = request.form['author']
        illustrator = request.form['illustrator']
        genre = request.form['genre']
        release = request.form['release']
        description = request.form['descrip']

        # Load or create the DataFrame
        if os.path.exists(BOOK_FILE):
            df = pd.read_excel(BOOK_FILE)
            
            # Check if 'ID' column exists, if not, add it with incrementing IDs
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
            new_id = df['ID'].max() + 1  # Increment ID based on max existing ID
        else:
            # Create a new DataFrame with the necessary columns if file doesn't exist
            df = pd.DataFrame(columns=['ID', 'title', 'author', 'illustrator', 'genre', 'release', 'descrip', 'bookcover'])
            new_id = 1  # Start IDs from 1

        # Check if the book already exists in database
        if not df[df['title'] == title].empty:
            message = "Book already added"
            return render_template('addbook.html', message=message)

        # Add new user to DataFrame
        new_user = pd.DataFrame([{
            'ID': new_id,
            'title': title,
            'author': author,
            'illustrator': illustrator,
            'genre': genre,
            'release': release,
            'bookcover': book_cover_path
        }])
        df = pd.concat([df, new_user], ignore_index=True)
        df.to_excel(BOOK_FILE, index=False)

    return render_template('addbook.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home_page'))

if __name__ == '__main__':
    app.run(debug=True)