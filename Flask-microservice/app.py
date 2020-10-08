"""Main application file"""
from flask import Flask
app = Flask(__name__)

@app.route('/api/<random_string>')
def returnBackwardsString(random_string):
    """Reverse and return the provided URI"""
    return "".join(reversed(random_string))

@app.route('/buritos/')
def index():
    return "The URL for this page is Buritos"

@app.route('/')
def indexmain():
    return "The is main"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
