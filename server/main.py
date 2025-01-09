from flask import Flask
from flasgger import Swagger


app = Flask(__name__)
swagger = Swagger(app)


@app.route('/add_service', methods=['POST'])
def add_service():
    """
    ---
    return:
    """
    pass


@app.route('/long_to_short', methods=['POST'])
def long_to_short():
    pass


@app.route('/alerting_jobs', methods=['GET'])
def get_alerting_jobs():
    pass


@app.route('/del_job', methods=['DELETE'])
def del_job():
    pass


if __name__ == '__main__':
    app.run(debug=True)
