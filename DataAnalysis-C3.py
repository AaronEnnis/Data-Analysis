import os, nltk, json, pymongo, hashlib, hmac, codecs
from collections import Counter
from nltk.tokenize import sent_tokenize, word_tokenize, RegexpTokenizer
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'Uploaded_Files'                                ##file uploads path
ALLOWED_EXTENSIONS = set(['txt', 'text', 'rtf', 'wtx'])

client = pymongo.MongoClient()                                  ##data base
db = client['DataAnalysis']
c = db['norms'] 

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def make_token(filename):               ##tokenizes contents of a textual file
    f = codecs.open(filename, encoding = 'utf-8', errors = 'ignore')
    word = []
    for line in f:
        word.append(line.lower())

    the_sent = "".join(word)
    words_digest = sha_hash = hashlib.sha256(bytes(the_sent, encoding='utf-8')).hexdigest()            ##hashing the files contents
    token = RegexpTokenizer(r'\w+')
    tokenized_list = token.tokenize(the_sent)
    return tokenized_list, words_digest


def check_json(tokens):                                     ##compares tokens to json file
    with open('ea-thesaurus-lower.json') as normsf:                 
        norms = json.load(normsf)
    tokens_set = set(tokens)
    tokenized_words = tokens_set
    compared_words = []
    invalid_words = []
    for w in tokenized_words:
        print(w)
    for w in tokenized_words:
        if w not in norms:
            invalid_words.append(w)
        else:
            associations = (w, norms[w][:3])
            compared_words.append(associations)
    return compared_words, invalid_words

def compare_hash_value(hash_value, hash_set):
    for h in hash_set:                
        if hmac.compare_digest(hash_value, h):
            return False
    return True

                    

@app.route('/')
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            tokens, hash_value = make_token(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            token_count  = Counter(tokens)
            word_freq = {}
            for k, v in token_count.items():
                word_freq.update({k:v})
            associated_words, invalid_words = check_json(tokens)

            hash_list = []
            
            for w in c.find():
                hash_list.append(w['hashValue'])
            hash_set = set(hash_list)
            
            if compare_hash_value(hash_value, hash_set):         ##checks if file is already uploaded                
                c.insert(  { 'file': filename,
                          'hashValue': hash_value,
                          'frequent': word_freq,                
                          'associated': associated_words,
                          'invalid': invalid_words}, check_keys = False)
                
           
            return render_template('display.html',
                                   title = 'words',
                                   file = filename,
                                   json_words = sorted(associated_words),
                                   frequency = word_freq,
                                   invalid = sorted(invalid_words))
    return render_template('upload.html',
                           title = 'upload')

@app.route('/results')
def results():
    file_list = []
    files = request.form.getlist('file_handles[]')
    for w in c.find():
        file_list.append(w['file'])
    files = file_list

    data_list = []
    data = request.form.getlist('data_handles[]')
    for w in c.find():
        data_list.append(w)
    data = data_list
        
    return render_template('results.html',
                           title = 'results',
                           files = files,
                           data = data)

app.secret_key = 'thisissecret'

if __name__ == '__main__':    
    app.run(debug = True)
