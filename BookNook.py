from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for sessions

USER_FILE = 'users.xlsx'
BOOK_FILE = 'books.xlsx'
REVIEW_FILE = 'review.xlsx'
PROFILE_PIC_FOLDER = 'static/profile_pics'
BOOK_COVER_FOLDER = 'static/book_covers'
USER_DB_FOLDER = 'user_databases'
os.makedirs(PROFILE_PIC_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist
os.makedirs(BOOK_COVER_FOLDER, exist_ok=True)
os.makedirs(USER_DB_FOLDER, exist_ok=True)

@app.route('/')
def home():
    # Path to the reviews file
    REVIEW_FILE = 'review.xlsx'
    BOOK_FILE = 'books.xlsx'
    
    # Initialize recent_reviews as an empty list in case the file does not exist
    recent_reviews = []
    recent_books = []

    # Check if the reviews file exists
    if os.path.exists(REVIEW_FILE):
        # Read the reviews from the file
        review_df = pd.read_excel(REVIEW_FILE)

        # Sort reviews by ID (assuming higher IDs are more recent)
        review_df = review_df.sort_values(by='ID', ascending=False)

        # Get the top 3 most recent reviews
        recent_reviews = review_df.head(3).to_dict(orient='records')  # Convert to a list of dictionaries

    if os.path.exists(BOOK_FILE):
        book_df = pd.read_excel(BOOK_FILE)
        
        book_df = book_df.sort_values(by='ID', ascending=False)

        # Check if the 'book_cover' column exists and handle missing or invalid data
        if 'book_cover' in book_df.columns:
            # Replace NaN or invalid values with a default image (optional)
            book_df['book_cover'] = book_df['book_cover'].fillna('default_cover.jpg').astype(str)

            recent_books = book_df.head(3).to_dict(orient='records')
        
    # Pass the reviews and books to the template
    return render_template('home.html', recent_reviews=recent_reviews, recent_books=recent_books)

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
        bio = request.form['bio']

        # Load or create the main user DataFrame
        if os.path.exists(USER_FILE):
            df = pd.read_excel(USER_FILE)
            if 'ID' not in df.columns:
                df['ID'] = range(1, len(df) + 1)
            new_id = df['ID'].max() + 1
        else:
            df = pd.DataFrame(columns=['ID', 'username', 'password', 'surname', 'forename', 'email', 'birth', 'bio', 'profile_pic'])
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
            'bio': bio,
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

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    # Ensure the user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Get the logged-in user's username
    logged_in_user = session['username']

    # Paths to the .xlsx files for both users
    logged_in_user_file = os.path.join(USER_DB_FOLDER, f"{logged_in_user}.xlsx")
    followed_user_file = os.path.join(USER_DB_FOLDER, f"{username}.xlsx")

    # Check if the user files exist
    if not os.path.exists(logged_in_user_file) or not os.path.exists(followed_user_file):
        return "One or more user files not found", 404

    # Add the logged-in user to the followed user's followers list
    add_to_followers(followed_user_file, logged_in_user)

    # Add the followed user to the logged-in user's following list
    add_to_following(logged_in_user_file, username)

    return redirect(url_for('account', username=username))

def get_user_id(username):
    if os.path.exists(USER_FILE):
        df = pd.read_excel(USER_FILE)
        user = df[df['username'] == username]
        return int(user['ID'].values[0]) if not user.empty else None
    return None

# Helper function to add the logged-in user to the followed user's followers sheet
def add_to_followers(file_path, username):
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        
        # Extract the followers column as a list (handling empty values)
        followers = eval(df['followers'].iloc[0]) if not pd.isna(df['followers'].iloc[0]) else []

        # Avoid duplicates
        if username not in followers:
            followers.append(username)
            df.at[0, 'followers'] = str(followers)  # Update the followers column with the new list
        
        # Save the updated DataFrame back to the file
        df.to_excel(file_path, index=False)

def add_to_following(file_path, username):
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        
        # Extract the following column as a list (handling empty values)
        following = eval(df['following'].iloc[0]) if not pd.isna(df['following'].iloc[0]) else []

        # Avoid duplicates
        if username not in following:
            following.append(username)
            df.at[0, 'following'] = str(following)  # Update the following column with the new list
        
        # Save the updated DataFrame back to the file
        df.to_excel(file_path, index=False)
        
@app.route('/account/<username>/followers')
def followers(username):
    user_file = os.path.join(USER_DB_FOLDER, f"{username}.xlsx")
    
    # Check if the user's file exists
    if not os.path.exists(user_file):
        return f"No database found for user {username}", 404

    # Load the user's followers list
    df = pd.read_excel(user_file)
    followers = eval(df['followers'].iloc[0]) if not pd.isna(df['followers'].iloc[0]) else []

    # Load the main users database to fetch details of followers
    if os.path.exists(USER_FILE):
        users_df = pd.read_excel(USER_FILE)
        followers_details = users_df[users_df['username'].isin(followers)].to_dict('records')
    else:
        followers_details = []

    return render_template('followers.html', username=username, followers_details=followers_details)
    
    
@app.route('/account/<username>/following')
def following(username):
    user_file = os.path.join(USER_DB_FOLDER, f"{username}.xlsx")
    
    # Check if the user's file exists
    if not os.path.exists(user_file):
        return f"No database found for user {username}", 404

    # Load the user's following list
    df = pd.read_excel(user_file)
    following = eval(df['following'].iloc[0]) if not pd.isna(df['following'].iloc[0]) else []

    # Load the main users database to fetch details of followings
    if os.path.exists(USER_FILE):
        users_df = pd.read_excel(USER_FILE)
        following_details = users_df[users_df['username'].isin(following)].to_dict('records')
    else:
        following_details = []

    return render_template('following.html', username=username, following_details=following_details)
    
@app.route('/addbook', methods=['GET', 'POST'])
def add_book():
   
    if request.method == 'POST':
        # Handle book cover upload
        book_cover = request.files['bookcover']
        if book_cover:
            cover_filename = book_cover.filename
            book_cover_path = f"book_covers/{cover_filename}"
            book_cover.save(os.path.join(BOOK_COVER_FOLDER, cover_filename))

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
            'description': description,
            'book_cover': book_cover_path
        }])
        df = pd.concat([df, new_user], ignore_index=True)
        df.to_excel(BOOK_FILE, index=False)

    return render_template('addbook.html')

@app.route('/book/<title>')
def book(title):
    # Load user data from file
    if not os.path.exists(BOOK_FILE):
        return "User database not found", 404

    df = pd.read_excel(BOOK_FILE)
    title = df[df['title'] == title]

    if title.empty:
        return "User not found", 404

    title_info = title.iloc[0].to_dict()  # Get user data as a dictionary
    

    return render_template('book.html', title_info=title_info)
    
@app.route('/books')
def books():
    if not os.path.exists(BOOK_FILE):
        return "Book database not found", 404

    # Load all books from the database
    df = pd.read_excel(BOOK_FILE)
    books_list = df.to_dict('records')  # Convert each row to a dictionary

    return render_template('book_page.html', books=books_list)
    
@app.route('/addreview', methods=['GET', 'POST'])
def add_review():
    if request.method == 'GET':
        # Render the addreview.html page for GET requests
        return render_template('addreview.html')

    # Handle POST request
    title = request.form.get('title')  # Use get to avoid KeyError if title is missing
    if not title:
        message = "Title is required."
        return render_template('addreview.html', message=message)

    rating = request.form.get('rating')
    review = request.form.get('review')

    # Check if the BOOK_FILE exists
    if os.path.exists(BOOK_FILE):
        book_df = pd.read_excel(BOOK_FILE)

        # Check if the book title exists in the BOOK_FILE
        if book_df[book_df['title'] == title].empty:
            message = f"Book '{title}' isn't in the database."
            return render_template('addreview.html', message=message)
    else:
        message = "No book database found."
        return render_template('addreview.html', message=message)

    # Check if the REVIEW_FILE exists
    if os.path.exists(REVIEW_FILE):
        review_df = pd.read_excel(REVIEW_FILE)

        # Ensure the 'ID' column exists; if not, initialize it
        if 'ID' not in review_df.columns:
            review_df['ID'] = range(1, len(review_df) + 1)
        new_id = review_df['ID'].max() + 1  # Increment ID based on max existing ID
    else:
        # Create a new DataFrame with the necessary columns if file doesn't exist
        review_df = pd.DataFrame(columns=['ID', 'title', 'rating', 'review', 'user_id'])
        new_id = 1  # Start IDs from 1

    # Get the logged-in user's ID
    logged_in_user = session.get('username')  # Get the logged-in username from the session
    user_id = get_user_id(logged_in_user)  # Retrieve the user's ID from the users.xlsx

    if user_id is None:
        message = "User ID not found. Please log in again."
        return render_template('addreview.html', message=message)

    # Add new review to DataFrame, including the user_id
    new_review = pd.DataFrame([{
        'ID': new_id,
        'title': title,
        'rating': rating,
        'review': review,
        'user_id': user_id  # Add the user ID to the review
    }])
    review_df = pd.concat([review_df, new_review], ignore_index=True)
    review_df.to_excel(REVIEW_FILE, index=False)

    # Success message
    message = "Review added successfully!"
    return render_template('addreview.html', message=message)
    
@app.route('/search')
def search():
    search_query = request.args.get('q', '').strip().lower()  # Get the search query

    if not search_query:
        return render_template('search.html', books=[], accounts=[], search_query=search_query)

    # Search for books in the database
    books_df = pd.read_excel(BOOK_FILE) if os.path.exists(BOOK_FILE) else pd.DataFrame()
    books_df = books_df[
        books_df['title'].str.contains(search_query, case=False, na=False) |
        books_df['author'].str.contains(search_query, case=False, na=False) |
        books_df['illustrator'].str.contains(search_query, case=False, na=False) |
        books_df['genre'].str.contains(search_query, case=False, na=False)
    ]
    books_list = books_df.to_dict('records')

    # Optionally, search for accounts if needed (example structure)
    accounts_df = pd.read_excel(USER_FILE) if os.path.exists(USER_FILE) else pd.DataFrame()
    accounts_df = accounts_df[
        accounts_df['username'].str.contains(search_query, case=False, na=False) |
        accounts_df['forename'].str.contains(search_query, case=False, na=False) |
        accounts_df['surname'].str.contains(search_query, case=False, na=False)
    ]
    accounts_list = accounts_df.to_dict('records')

    return render_template('search.html', books=books_list, accounts=accounts_list, search_query=search_query)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)