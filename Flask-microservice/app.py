"""Main application file"""
import flask
import datetime
import platform
import os

app = flask.Flask(__name__)



@app.route('/api/<random_string>')
def returnBackwardsString(random_string):
    """Reverse and return the provided URI"""
    return "".join(reversed(random_string))

@app.route('/buritos/')
def index():
    return "The URL for this page is Buritos"

@app.route('/other/')
def indexmain():
    return "The is main"


@app.route('/')
def hello():
    name = flask.request.args.get("name", "Flask-demo")
    time = datetime.datetime.now()
    python_version = platform.python_version()
    aws_platform = os.environ.get('PLATFORM', 'Amazon Web Services')
    return flask.render_template('index.html',
                                 platform=aws_platform,
                                 flask_version=flask.__version__,
                                 python_version=python_version,
                                 flask_url='https://palletsprojects.com/p/flask/',
                                 time=time,
                                 name=name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
