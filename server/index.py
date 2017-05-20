import os
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from passporteye import read_mrz

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__, static_url_path='/static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# @app.route('/js/<path:path>')
# def send_js(path):
#     return send_from_directory('js', path)
#
# @app.route('/assets/<path:path>')
# def send_assets(path):
#     return send_from_directory('assets', path)

@app.route('/<path:path>')
def static_file(path):
    return app.send_static_file(path)

@app.route('/')
def root():
    return app.send_static_file('index.html')

@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            mrz = read_mrz(filepath)
            return mrz.names
        
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


# @app.route("/")
# def hello():
#     image_filename = "/Users/dmitry.zhukov/Projects/PassportEye/passporteye/mrz/testdata/100_pass-bdr.jpg"
#     mrz = read_mrz(image_filename)
#     return mrz.names

if __name__ == "__main__":
    app.run(host='0.0.0.0')