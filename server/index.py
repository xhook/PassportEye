import os

from flask import Flask, request, redirect, jsonify
from werkzeug.utils import secure_filename

from passporteye import read_mrz
import jellyfish

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__, static_url_path='/static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)


@app.route('/')
def root():
    return app.send_static_file('index.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
#            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
#            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            absolute_path = os.path.abspath(filename)
            file.save(absolute_path)
            result = read_mrz(absolute_path)
            result['first_name'] = request.form['first_name']
            return jsonify(result)

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


@app.route('/verify', methods=['POST'])
def verify():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        absolute_path = os.path.abspath(filepath)
        file.save(absolute_path)
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        result = verify_id(absolute_path, first_name, last_name, dob)
        return jsonify(result)


def compose_features(result, first_name, last_name, dob):
    jaro_first_names = jellyfish.jaro_distance(unicode(first_name.upper()), unicode(result['mrz']['names'].upper()))
    jaro_last_name = jellyfish.jaro_distance(unicode(last_name.upper()), unicode(result['mrz']['surname'].upper()))
    features = {
        'mrz_valid_score': result['mrz']['valid_score'],
        'ela_max_diff': result['ela']['max_diff'],
        # 'ela_histogram': [0.0] * 768,
        'mrz_document_type_lab_count': -1.0,
        'mrz_document_type_rab_count': -1.0,
        'mrz_country_lab_count': -1.0,
        'mrz_country_rab_count': -1.0,
        'mrz_country_has_digits': -1.0,
        'mrz_number_lab_count': -1.0,
        'mrz_number_rab_count': -1.0,
        'mrz_date_of_birth_lab_count': -1.0,
        'mrz_date_of_birth_rab_count': -1.0,
        'mrz_expiration_date_lab_count': -1.0,
        'mrz_expiration_date_rab_count': -1.0,
        'mrz_nationality_lab_count': -1.0,
        'mrz_nationality_rab_count': -1.0,
        'mrz_nationality_has_digits': -1.0,
        'mrz_sex_lab_count': -1.0,
        'mrz_sex_rab_count': -1.0,
        'mrz_names_lab_count': -1.0,
        'mrz_names_rab_count': -1.0,
        'mrz_last_name_lab_count': -1.0,
        'mrz_last_name_rab_count': -1.0,
        'mrz_personal_number_lab_count': -1.0,
        'mrz_personal_number_rab_count': -1.0,
        'date_of_birth_levenshtein': -1.0,
        'first_names_levenshtein': -1.0,
        'first_names_normalized_evenshtein': -1.0,
        'first_names_jaro_winkler': jaro_first_names,
        'last_name_levenshtein': -1.0,
        'last_name_normalized_evenshtein': -1.0,
        'last_name_jaro_winkler': jaro_last_name,
        'only_digits_in_mrz_date_of_birth': -1.0,
        'only_digits_in_mrz_expiration_date': -1.0,
        'mrz_type_idx': -1.0,
        'mrz_document_type_idx': -1.0,
        'mrz_country_idx': -1.0,
        'mrz_nationality_idx': -1.0,
        'mrz_sex_idx': -1.0,
    }
    return features


def predict(features):
    valid_score = features['mrz_valid_score'] * 0.01
    jaro_score = features['first_names_jaro_winkler'] * features['last_name_jaro_winkler']
    score = valid_score * jaro_score
    return {
        'score': score,
        'valid': score > 0.9
    }


def verify_id(filepath, first_name, last_name, dob):
    result = read_mrz(filepath)
    features = compose_features(result, first_name, last_name, dob)
    prediction = predict(features)
    prediction['metadata'] = {
        'first_name': result['mrz']['names'].upper(),
        'last_name': result['mrz']['surname'].upper()
    }
    return prediction


if __name__ == "__main__":
    app.run(host='0.0.0.0')
