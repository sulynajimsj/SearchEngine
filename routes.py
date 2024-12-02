import json
import logging
from bottle import route, run, template, request, static_file, redirect, response, debug
from oauth2client.client import flow_from_clientsecrets
from logic.auth_manager import AuthenticationManager
from logic.search_manager import SearchManager

debug(True)

# Initialize managers
auth_manager = AuthenticationManager()
search_manager = SearchManager()
logger = logging.getLogger(__name__)

# Google OAuth2 flow setup
flow = flow_from_clientsecrets(
    "client_secrets.json",
    scope=[
        'https://www.googleapis.com/auth/plus.me',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ],
    redirect_uri='http://localhost:8080/redirect'
)


@route('/static/<filename:path>')
def send_static(filename):
    return static_file(filename, root='./static')


@route('/', method=['GET'])
def home():
    session_token = request.get_cookie("session_token")
    if auth_manager.validate_session(session_token):
        return redirect('/home')
    return template('template/login.html')


@route('/login', method=['GET'])
def login():
    # Direct users to Google's OAuth2 consent screen
    return redirect(flow.step1_get_authorize_url())


@route('/redirect')
def redirect_page():
    try:
        code = request.query.get('code', "")
        session_data = auth_manager.process_oauth_callback(code, flow)

        if session_data:
            response.set_cookie("session_token", session_data.session_token, path='/')
            return redirect('/home')

        return redirect('/')
    except Exception as e:
        logger.error(f"Error in redirect: {e}")
        return redirect('/')


@route('/home', method=['GET'])
def search():
    session_token = request.get_cookie("session_token")
    session_data = auth_manager.validate_session(session_token)

    # Handle AJAX requests for autocomplete
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        query = request.query.get('q', '')
        return json.dumps(search_manager.get_suggestions(query))

    keyword_input = request.query.get('keywords', '')
    if not keyword_input:
        return template(
            'template/query_page.html',
            user_name=session_data.name if session_data else None,
            user_email=session_data.email if session_data else None,
            user_picture=session_data.picture if session_data else None,
            recent_searches=[]
        )

    page = int(request.query.get('page', 1))
    search_results, result_counts, total_results = search_manager.search(keyword_input, page)
    total_pages = (total_results + search_manager.per_page - 1)

    return template(
        'template/results.html',
        result_counts=result_counts,
        search_results=search_results,
        recent_searches=[],
        query=keyword_input,
        user_name=session_data.name if session_data else None,
        user_email=session_data.email if session_data else None,
        user_picture=session_data.picture if session_data else None,
        current_page=page,
        total_pages=total_pages,
        total_results=total_results
    )


@route('/logout')
def logout():
    session_token = request.get_cookie("session_token")
    auth_manager.end_session(session_token)
    response.delete_cookie("session_token")
    return redirect('/')


if __name__ == '__main__':
    run(host='0.0.0.0', port=8080, debug=True)