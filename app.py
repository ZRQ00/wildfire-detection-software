from flask import Flask, request, jsonify, render_template
# Import model later

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check_risk():
    pass


if __name__ == '__main__':
    app.run(debug=True)
    
