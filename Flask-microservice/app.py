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

# @app.route('/hello')
# def hello():
#     name = flask.request.args.get("name", "Flask-demo")
#     time = datetime.datetime.now()
#     python_version = platform.python_version()
#     aws_platform = os.environ.get('PLATFORM', 'Ben Platform')
#     return flask.render_template('hello.html',
#                                  platform=aws_platform,
#                                  flask_version=flask.__version__,
#                                  python_version=python_version,
#                                  flask_url='https://palletsprojects.com/p/flask/',
#                                  time=time,
#                                  name=name)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
