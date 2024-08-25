from flask import Flask, render_template, request, jsonify
from utils import search_keywords
from utils import make_sentences

app = Flask(__name__)

@app.route('/')
def index():
    # index.htmlを返却する。
    # templates というフォルダの中に絶対いれる。
    return render_template('index.html')

# index.htmlからPOSTを受け取ったときに
@app.route('/execute_function', methods=['POST'])
def execute_function():
    # 実行したい関数をここに書く
    if 'input1' in request.form:
        result = search_keywords(request.form['input1'])
    elif 'input2' in request.form:
        make_sentences(request.form['input2'])
        result = "Maked a sentcence."
    else:
        result = "No input recognized."
    return jsonify(result=result)

if __name__ == '__main__':
    app.run(debug=True)