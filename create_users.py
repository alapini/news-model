import subprocess
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client.twitter_news

users = 100

for idx in range(users):
    uname = f'user_{idx}'
    password = subprocess.check_output(['./mkpassword', '3'])
    password = password.decode('utf-8')[:-1]

    print(uname, password, sep='\t')

    db.users.insert_one({'username': uname, 'password': password})
