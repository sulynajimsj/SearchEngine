import sqlite3
import uuid
import httplib2
import json
from bottle import route, run, template, request, static_file, redirect, response
from oauth2client.client import flow_from_clientsecrets, OAuth2Credentials
from googleapiclient.discovery import build
import traceback
from bottle import debug
debug(True)


# Load or initialize persistent data storage
try:
    with open('data.json', 'r') as f:
        persistent_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    persistent_data = {"users": {}, "search_history": {}}

# In-memory session storage
sessions = {}

# Google OAuth2 flow
flow = flow_from_clientsecrets("client_secrets.json",
                               scope=['https://www.googleapis.com/auth/plus.me',
                                      'https://www.googleapis.com/auth/userinfo.email',
                                      'https://www.googleapis.com/auth/userinfo.profile'],
                               redirect_uri='http://localhost:8080/redirect')


# Save persistent data to JSON file
def save_data():
    with open('data.json', 'w') as f:
        json.dump(persistent_data, f)


# Serve static files (like images)
@route('/static/<filename:path>')
def send_static(filename):
    return static_file(filename, root='./static')


# Home route for login redirection
@route('/', method=['GET'])
def home():
    session_token = request.get_cookie("session_token")
    if session_token in sessions:
        return redirect('/home')
    return template('login.html')


@route('/login', method=['GET'])
def login():
    user_email = request.get_cookie("user_email")

    # Check if the user is already registered in persistent_data
    if user_email and user_email in persistent_data["users"]:
        # Check if we already have stored credentials
        user_data = persistent_data["users"][user_email]
        credentials_json = user_data.get("credentials")
        refresh_token = user_data.get("refresh_token")

        if credentials_json and refresh_token:
            credentials = OAuth2Credentials.from_json(credentials_json)

            # Refresh token if access token is expired
            if credentials.access_token_expired:
                try:
                    credentials.refresh(httplib2.Http())
                    # Save refreshed credentials
                    persistent_data["users"][user_email]["credentials"] = credentials.to_json()
                    save_data()
                except Exception as e:
                    print(f"Failed to refresh credentials: {e}")
                    return redirect('/login')

            # Create a new session with refreshed or valid credentials
            session_token = str(uuid.uuid4())
            sessions[session_token] = {
                "email": user_email,
                "name": user_data["name"],
                "picture": user_data["picture"]
            }
            response.set_cookie("session_token", session_token, path='/')
            return redirect('/home')

    # If no stored credentials, redirect to Google login for authorization
    return redirect(flow.step1_get_authorize_url())


@route('/redirect')
def redirect_page():
    try:
        code = request.query.get('code', "")
        credentials = flow.step2_exchange(code)

        user_email = credentials.id_token['email']

        # Check if the user is new or refresh token is missing
        if user_email not in persistent_data["users"]:
            persistent_data["users"][user_email] = {
                "name": credentials.id_token.get('name', 'Unknown'),
                "picture": credentials.id_token.get('picture', ''),
                "refresh_token": credentials.refresh_token,
                "credentials": credentials.to_json()  # Store full credentials JSON
            }
            persistent_data["search_history"][user_email] = []
        else:
            # Update credentials and refresh token if available
            persistent_data["users"][user_email]["credentials"] = credentials.to_json()
            if credentials.refresh_token:
                persistent_data["users"][user_email]["refresh_token"] = credentials.refresh_token

        save_data()

        session_token = str(uuid.uuid4())
        sessions[session_token] = {
            "email": user_email,
            "name": persistent_data["users"][user_email]["name"],
            "picture": persistent_data["users"][user_email]["picture"]
        }

        response.set_cookie("session_token", session_token, path='/')
        redirect('/home')

    except Exception as e:
        print(f"Error in setting up session: {e}")
        traceback.print_exc()
        redirect('/')


@route('/home', method=['GET'])
def search():
    session_token = request.get_cookie("session_token")
    session_data = sessions.get(session_token)

    # Check if there's a search query
    keyword_input = request.query.get('keywords', '')
    
    # If no search query, show the search interface
    if not keyword_input:
        return template('query_page.html',
                       user_name=session_data.get('name') if session_data else None,
                       user_email=session_data.get('email') if session_data else None,
                       user_picture=session_data.get('picture') if session_data else None,
                       recent_searches=[])

    # Get page number from query parameters, default to 1
    page = int(request.query.get('page', 1))
    per_page = 5  # Number of results per page

    # Database connection
    conn = sqlite3.connect('crawler.db')
    cursor = conn.cursor()

    if not session_data:
        # Handle unauthenticated users
        keyword_input = request.query.get('keywords', '')
        if keyword_input:
            keyword_list = keyword_input.split()
            result_counts = {}
            doc_id_matches = {}

            # First pass: count keywords and collect matching doc_ids
            for word in keyword_list:
                result_counts[word] = result_counts.get(word, 0) + 1

                cursor.execute("SELECT word_id FROM lexicon WHERE word = ?", (word,))
                word_id_result = cursor.fetchone()

                if word_id_result:
                    word_id = word_id_result[0]
                    cursor.execute("""
                        SELECT doc_id 
                        FROM inverted_index 
                        WHERE word_id = ?
                    """, (word_id,))

                    for (doc_id,) in cursor.fetchall():
                        doc_id_matches[doc_id] = doc_id_matches.get(doc_id, 0) + 1

            # Get search results only if we found matches
            search_results = []
            total_results = 0
            if doc_id_matches:
                placeholders = ','.join('?' * len(doc_id_matches))
                cursor.execute(f"""
                    SELECT doc_id, url, title, page_rank 
                    FROM doc_index 
                    WHERE doc_id IN ({placeholders})
                    ORDER BY page_rank DESC
                """, list(doc_id_matches.keys()))

                # Sort all results first
                results = cursor.fetchall()
                sorted_results = sorted(
                    [(doc_id, url, title, rank) for doc_id, url, title, rank in results],
                    key=lambda x: (-doc_id_matches[x[0]], -x[3])
                )

                # Calculate pagination
                total_results = len(sorted_results)
                total_pages = (total_results + per_page - 1) // per_page
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page

                # Slice the results for current page
                page_results = sorted_results[start_idx:end_idx]

                # Create final results list with sequential ranking
                for idx, (doc_id, url, title, _) in enumerate(page_results, start_idx + 1):
                    search_results.append({
                        'url': url,
                        'title': title if title else url,
                        'rank': idx,
                        'match_count': doc_id_matches[doc_id]
                    })

            conn.close()
            return template('results.html',
                            result_counts=result_counts,
                            search_results=search_results,
                            recent_searches=[],
                            query=keyword_input,
                            user_name=None,
                            user_email=None,
                            user_picture=None,
                            current_page=page,
                            total_pages=total_pages if doc_id_matches else 0,
                            total_results=total_results)

        # ... rest of the code remains the same ...


# Logout route to clear the session
@route('/logout')
def logout():
    session_token = request.get_cookie("session_token")
    if session_token in sessions:
        del sessions[session_token]
    response.delete_cookie("session_token")
    return redirect('/')


run(host='0.0.0.0', port=80, debug=True)
