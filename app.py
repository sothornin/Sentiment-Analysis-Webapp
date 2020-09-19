from flask import Flask, render_template, url_for, request,redirect
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import tweepy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
bootstrap = Bootstrap(app)

consumer_key = 'Nj7pYtoSKQhWdxOFhjO3VBGNB'
consumer_secret = 'JKNZX2yILqreg3vLadBWXRvB01nFrMZFRfqy4XowoJjjax0Ha2'
access_token = '1130490153460412416-Sh7f5IKGBxIgpsxG23u9Pg6Z3Oqr1j'
access_token_secret = 'gYxPDBdrcbbiPawmPQ9CkRCY1QNEQqA1LT2W76nIEqbhz'
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    #completed = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Task %r>' % self.id

@app.route('/',methods=['POST','GET'])
def index():
    if request.method == 'POST':
        tweet_query = request.form['content']
        tweet_number = int(request.form['number'])
        texts = []
        api = tweepy.API(auth,wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        search_words = tweet_query
        new_search = search_words + " -filter:retweets"
        search = tweepy.Cursor(api.search, q=new_search, lang="th", tweet_mode="extended").items(tweet_number)
        texts = [item.full_text for item in search]
        return render_template('index.html', tasks = texts)
        # for text in texts:
        #     try:
        #         db.session.add(text)
        #         db.session.commit()
        #         return redirect('/')
        #     except Exception as e:
        #         print(e)
        #         return 'There is an error'

        #return tweet_query
        # task_content = request.form['content']
        # /new_task = Todo(content=task_content)
        # try:
        #     db.session.add(new_task)
        #     db.session.commit()
        #     return redirect('/')
        # except Exception as e:
        #     print(e)
        #     return 'There is an error'

    else:
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks = tasks)

@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was Error'

@app.route('/update/<int:id>', methods=['GET','POST'])
def update(id):
    task = Todo.query.get_or_404(id)
    if request.method=='POST':
        task.content = request.form['content']
        try:
            db.session.commit()
            return redirect('/')
        except:
            print('error')
    else:
        return render_template('update.html',task=task)

if __name__ == "__main__":
    app.run(debug=True)