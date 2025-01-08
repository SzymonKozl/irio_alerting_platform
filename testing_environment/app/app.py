from flask import Flask, request, jsonify

app = Flask(__name__)
number_list = []

# Add a number to the list
@app.route('/add', methods=['POST'])
def add_number():
    number = request.json.get('number')
    if number is not None:
        number_list.append(number)
        return jsonify({"message": "Number added", "list": number_list}), 201
    return jsonify({"error": "Number not provided"}), 400

# Get the list of numbers
@app.route('/list', methods=['GET'])
def get_list():
    return jsonify({"list": number_list}), 200

# Health check
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
