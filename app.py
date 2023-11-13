import json
import os
from flask import Flask, request, render_template, redirect, url_for, session
import requests
from google.oauth2 import service_account
import gspread
from flask_httpauth import HTTPBasicAuth
from googleapiclient.discovery import build
import math

app = Flask(__name__)
auth = HTTPBasicAuth()

# セッションのシークレットキーを設定
app.secret_key = os.urandom(24)

# パスワードを設定
password = "scJsonApi2235"

# Google Driveの認証情報のファイルパス
drive_credentials_file = 'instagram.json'

# Google DriveのフォルダID（アップロード先フォルダ）
drive_folder_id = '1hgSRL25HUjX_Z-6IHHBg0QxRHfdQStQi'

# 画像をダウンロードしてローカルフォルダに保存する関数
def download_image(url, image):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(image, 'wb') as f:
                f.write(response.content)
            return True
        else:
            return False
    except Exception as e:
        print(f"Error downloading image: {str(e)}")
        return False

# ログインフォーム
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        entered_password = request.form['password']
        if username == 'sc2235' and entered_password == password:
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

# ログアウト
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ログイン後のページ
@app.route('/write_to_sheets', methods=['GET', 'POST'])
def write_to_sheets():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    json_data = None  # 初期化
    if request.method == 'POST':
        json_url = request.form['json_url']
        json_data = fetch_json_data(json_url)
        if json_data:
            write_to_google_sheets(json_data)
            return "Data has been added to Google Sheets."
        else:
            return "Error fetching or writing data."
    return render_template('index.html')

# JSONデータを取得する関数
def fetch_json_data(json_url):
    try:
        response = requests.get(json_url)
        if response.status_code == 200:
            response.encoding = 'utf-8'
            return response.json()
        else:
            return None
    except Exception as e:
        return None

# Google Sheetsにデータを書き込む関数
def write_to_google_sheets(json_data):
    # Google Sheetsの認証情報を設定
    credentials = service_account.Credentials.from_service_account_file(
        "instagram.json",
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    gc = gspread.Client(auth=credentials)

    # スプレッドシートを開く（スプレッドシートの名前を設定）
    spreadsheet_name = "instagram"
    worksheet_name = "insta"

    try:
        spreadsheet = gc.open(spreadsheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        # 存在しない場合、新しいスプレッドシートを作成
        spreadsheet = gc.create(spreadsheet_name)
        worksheet = spreadsheet.sheet1  #デフォルトのシートが1つ作成される
        worksheet.update_title(worksheet_name)
    else:
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # 指定したワークシート名が存在しない場合、新しいワークシートを作成
            worksheet = spreadsheet.add_worksheet(worksheet_name, rows=1, cols=1)

            # B2セルにprofilePicUrlを設定
            worksheet.update('B2', 'profilePicUrl')

            # G2からP2セルにdisplayUrlを設定
            display_urls = ['displayUrl1', 'displayUrl2', 'displayUrl3', 'displayUrl4', 'displayUrl5', 'displayUrl6', 'displayUrl7', 'displayUrl8', 'displayUrl9', 'displayUrl10']
            cell_range = 'G2:P2'
            worksheet.update(cell_range, [display_urls])

# 新しいデータをリストに変換
    values = []
    for item in json_data:
        if 'latestPosts' in item:
            latest_posts = item['latestPosts'][::-1]  # latest_postsリストを逆順にする

        # likesCountを追加
        likes_counts = []
        for i in range(5):
            if i < len(latest_posts):
                post = latest_posts[i]
                likes_count = post.get("likesCount", 0) 
                likes_counts.append(likes_count)
                
        #commentsCountを追加
        comment_counts = []
        for i in range(5):
            if i < len(latest_posts):
                post = latest_posts[i]
                comments_count = post.get("commentsCount",0)
                comment_counts.append(comments_count)

        # いいね合計、平均いいね数、平均いいね率
        total_likes = sum(likes_counts)
        average_likes = total_likes / len(likes_counts) if len(likes_counts) > 0 else 0
        average_like_rate = average_likes / item.get('postsCount', 1)
        
        #コメント合計、平均コメント数
        total_comments = sum(comment_counts)
        average_comments = total_comments / len(comment_counts) if len(comment_counts) > 0 else 0
        
        #小数点2位で切り捨て
        period = 2
        ave = average_like_rate
        average_rate_period = math.floor(ave * 10 ** period) / (10 ** period)
        average_rate_period = "{:.2f}%".format(average_rate_period)
        average_rate_period = average_rate_period.rjust(20)
        

        # 各フィールドの値を取得
        row_data = [
            item.get('id', ''),
            f'=IMAGE("{item.get("profilePicUrl", "")})',
            item.get('username', ''),
            item.get('fullName', ''),
            item.get('isBusinessAccount', ''),
            item.get('biography', ''),
        ]

        # latestPostsのdisplayUrlを追加
        display_urls = []
        for i in range(12):
            if i < len(latest_posts):
                post = latest_posts[i]
                display_url = post.get("displayUrl", "")
                display_urls.append(f'=IMAGE("{display_url}")')
            else:
                display_urls.append('')
        
        row_data.extend(display_urls)
        
        row_data.extend([
            item.get("url", ""),
            item.get("externalUrl", ""),
            item.get("followersCount", ""),
            item.get("followsCount", ""),
            item.get("postsCount", ""),
        ])
        

        
            # いいね合計をX列、平均いいね数をY列、平均いいね率をZ列に追加
        row_data.extend([total_likes, average_likes,average_rate_period])
        
            # コメント合計、平均コメント率
        row_data.extend([total_comments,average_comments])
        
            # likesCountを追加
        row_data.extend(likes_counts)
        
            #commentcountを追加
        row_data.extend(comment_counts)
        
        



        # 新しいデータをリストに追加
        values.append(row_data)

# データをGoogle Sheetsに挿入
    worksheet.insert_rows(values, 2)


@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        json_url = request.form['json_url']
        json_data = fetch_json_data(json_url)
        if json_data:
            write_to_google_sheets(json_data)
            return "Data has been added to Google Sheets."
        else:
            return "Error fetching or writing data."
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
