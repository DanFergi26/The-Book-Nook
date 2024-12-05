#imports
from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for sessions

#Path to all the databases and image folders within the site
USER_FILE = 'users.xlsx'
BOOK_FILE = 'books.xlsx'
REVIEW_FILE = 'review.xlsx'
PROFILE_PIC_FOLDER = 'static/profile_pics'
BOOK_COVER_FOLDER = 'static/book_covers'
USER_DB_FOLDER = 'user_databases'

#Create the folders if they don't already exist
os.makedirs(PROFILE_PIC_FOLDER, exist_ok=True)  
os.makedirs(BOOK_COVER_FOLDER, exist_ok=True)
os.makedirs(USER_DB_FOLDER, exist_ok=True)

@app.route('/')
def home():

    # Initialize recent_reviews and recent_books as an empty list in case the file does not exist
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

    # Check if the book file exists
    if os.path.exists(BOOK_FILE):
        book_df = pd.read_excel(BOOK_FILE)
        
        book_df = book_df.sort_values(by='ID', ascending=False)

        # Check if the 'book_cover' column exists and handle missing or invalid data
        if 'book_cover' in book_df.columns:
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
            'ID': new_id, 
            'followers': [],  
            'following': [],   
            'upcoming_reads': []
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
     
    #Gather login data
    if request.method == 'POST':
        username = request.form['uname']
        password = request.form['pass']

        #Check if the user file exists
        if os.path.exists(USER_FILE):
            df = pd.read_excel(USER_FILE)
            user = df[df['username'] == username]
    
            #Check if username or password match the user database
            if user.empty:
                message = "Account doesn't exist"
            elif user['password'].values[0] != password:
                message = "The password is incorrect"
                
            #Set session login status and redirect to account page
            else:
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('account', username=username))
                
        #Alt message for if no accounts exists      
        else:
            message = "No registered users found."

    return render_template('login.html', message=message)

@app.route('/account/<username>')
def account(username):
    # Ensure user database exists
    if not os.path.exists(USER_FILE):
        return "User database not found", 404

    # Load user data from file
    df = pd.read_excel(USER_FILE)
    user = df[df['username'] == username]

    if user.empty:
        return "User not found", 404
        
    # Get user data as a dictionary
    user_info = user.iloc[0].to_dict()  

    # Load upcoming reads for the user
    user_file = os.path.join(USER_DB_FOLDER, f"{username}.xlsx")
    upcoming_reads = []

    if os.path.exists(user_file):
        user_df = pd.read_excel(user_file)

        if 'upcomingreads' in user_df.columns:
        
            # Get upcoming reads titles
            upcoming_titles = user_df['upcomingreads'].dropna().tolist()

            # Load books database to fetch matching book covers
            if os.path.exists(BOOK_FILE):
                books_df = pd.read_excel(BOOK_FILE)

                # Ensure necessary columns exist in books.xlsx
                if 'title' in books_df.columns and 'book_cover' in books_df.columns:
                
                    # Match titles and retrieve book covers
                    books_df['title'] = books_df['title'].str.strip().str.lower()
                    upcoming_reads = [
                        {
                            'title': title,
                            'cover': books_df.loc[books_df['title'] == title.lower(), 'book_cover'].iloc[0]
                        }
                        for title in upcoming_titles
                        if not books_df[books_df['title'] == title.lower()].empty
                    ]
                    
    user_id = get_user_id(username)
    if user_id is None:
        return "User not found", 404

    # Load user details
    df = pd.read_excel(USER_FILE)
    user = df[df['username'] == username]
    user_info = user.iloc[0].to_dict() 

    # Load reviews
    reviews_file = REVIEW_FILE  
    recent_reviews = []
    if os.path.exists(reviews_file):
        reviews_df = pd.read_excel(reviews_file)

        # Filter reviews by user_id and sort by ID (assuming higher ID = more recent)
        user_reviews = reviews_df[reviews_df['user_id'] == user_id].sort_values(by='ID', ascending=False)

        # Get the last 3 reviews
        recent_reviews = user_reviews.head(3).to_dict(orient='records')

    return render_template('account.html', user_info=user_info, upcoming_reads=upcoming_reads,  recent_reviews=recent_reviews)
    
@app.route('/upcomingreads', methods=['GET', 'POST'])
def upcoming_reads():
    # Ensure the user is logged in
    username = session.get('username')
    if not username:
        return "User not logged in", 403

    # Paths to user file and books file
    user_file = os.path.join(USER_DB_FOLDER, f"{username}.xlsx")
    books_file = BOOK_FILE
    message = None

    if request.method == 'POST':
        # Get the book title from the form
        title = request.form.get('title', '').strip()  
        if not title:
            message = "Book title is required."
        else:
            try:
                # Check if the books database exists
                if not os.path.exists(books_file):
                    message = "Books database not found."
                else:
                    # Load books database
                    books_df = pd.read_excel(books_file)

                    # Ensure 'title' column exists
                    if 'title' not in books_df.columns:
                        message = "'title' column is missing in books.xlsx."
                    else:
                        # Normalize titles in books_df for comparison
                        books_df['title'] = books_df['title'].str.strip().str.lower()
                        normalized_title = title.lower()

                        # Check if the book exists in books.xlsx
                        if normalized_title not in books_df['title'].values:
                            message = f"'{title}' isn't in the database."
                        else:
                            # Book exists, update the user's file
                            if os.path.exists(user_file):
                                user_df = pd.read_excel(user_file)
                            else:
                                # Create a new file if it doesn't exist
                                user_df = pd.DataFrame(columns=['upcomingreads'])

                            # Ensure 'upcomingreads' column exists
                            if 'upcomingreads' not in user_df.columns:
                                user_df['upcomingreads'] = pd.NA

                            # Append the new book
                            new_entry = pd.DataFrame({'upcomingreads': [title]})
                            user_df = pd.concat([user_df, new_entry], ignore_index=True)

                            # Save the updated file
                            user_df.to_excel(user_file, index=False)
                            message = f"'{title}' has been added to your upcoming reads!"

            except Exception as e:
                # Log any exceptions for debugging
                message = f"An error occurred: {str(e)}"

    return render_template('upcomingreads.html', message=message)
        
        

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
    #Check if the user database exists
    if os.path.exists(USER_FILE):
        #Read from the database
        df = pd.read_excel(USER_FILE)
        #Grab the user's ID using the username
        user = df[df['username'] == username]
        return int(user['ID'].values[0]) if not user.empty else None
    return None


def add_to_followers(file_path, username):
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        
        # Extract the followers column as a list (handling empty values)
        followers = eval(df['followers'].iloc[0]) if not pd.isna(df['followers'].iloc[0]) else []

        # Avoid duplicates
        if username not in followers:
            followers.append(username)
            df.at[0, 'followers'] = str(followers)  
        
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
            df.at[0, 'following'] = str(following) 
        
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

        # Add new book to Database
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
    #Check if the book database exists
    if not os.path.exists(BOOK_FILE):
        return "Book database not found", 404

    #Read data from the book database
    df = pd.read_excel(BOOK_FILE)
    title = df[df['title'] == title]

    if title.empty:
        return "Book not found", 404
        
    # Get book data as a dictionary
    title_info = title.iloc[0].to_dict()  
    

    return render_template('book.html', title_info=title_info)
    
@app.route('/books')
def books():
    #Check if book database exists
    if not os.path.exists(BOOK_FILE):
        return "Book database not found", 404

    # Load all books from the database
    df = pd.read_excel(BOOK_FILE)
    # Convert each row to a dictionary
    books_list = df.to_dict('records')  

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
    # Get the search query
    search_query = request.args.get('q', '').strip().lower()  

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

    # Search for accounts if needed 
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
    #Clear the session and redirect to home page
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)