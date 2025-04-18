from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "Hello, world!"})

@app.route('/api/test')
def test():
    return jsonify([
        {"id": 1, "name": "Test Item 1"},
        {"id": 2, "name": "Test Item 2"},
        {"id": 3, "name": "Test Item 3"}
    ])

if __name__ == '__main__':
    print("Starting minimal Flask app on port 8000")
    app.run(host='0.0.0.0', port=8000, debug=True) 