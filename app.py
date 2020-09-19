from flask import Flask, render_template, url_for, request,redirect
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
import tweepy
from datetime import datetime
import emoji
from pythainlp.corpus.common import thai_stopwords
from pythainlp import sent_tokenize, word_tokenize
#from pythainlp.ulmfit import process_thai
from pythainlp.util import normalize
import re
import itertools
import dill as pickle
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer

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

with open(f'model/clf.pkl', 'rb') as f:
    clf_model = pickle.load(f)

with open(f'model/tfidf.pickle', 'rb') as f:
    tfidf_model = pickle.load(f)

with open(f'model/support.pickle', 'rb') as f:
    support = pickle.load(f)

def text_cleaning(text):
  #emoji list
  emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
  #delte hashtag and mention
  text = re.sub(r"(?:@\S*|#\S*|http(?=.*://)\S*)", "",text)
  #delete emoji
  text = re.sub(r"^https://t.co/[A-Za-z0-9]*\s","",text)
  text = re.sub(r"\s+https://t.co/[a-zA-Z0-9]*\s", "", text)
  text = re.sub(r"\s+https://t.co/[a-zA-Z0-9]*$", "", text)
  text = emoji_pattern.sub(r"", text)
  text = re.sub("\d+", "", text) #number
  text = text.replace(" ","")
  text = re.sub('[^ก-๙]',"",text)
  text = normalize(text)
  tokens = word_tokenize(text)
  i = 0
  for token in list(tokens):
    if(len(token) == 1 or len(token) == token.count(token[0]) or token == 'xxrep'
    or token == 'xxwrep' or token == ''):
      tokens.pop(i)
      i = i-1
    i = i+1

  return tokens

stop_words = thai_stopwords() 
def delete_stop(word_list):
  clean_word = []
  for w in word_list:
    filtered_sentence = []
    for t in w: 
      if t not in stop_words:
        #t = ''.join(c[0] for c in itertools.groupby(t))
        filtered_sentence.append(t)
    clean_word.append(','.join(filtered_sentence))
  return clean_word  


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
        word_list = [text_cleaning(text) for text in texts]


        from pythainlp.tag import pos_tag_sents
        pos = pos_tag_sents(word_list,corpus='orchid_ud')
        keep_tag = ['VERB', 'ADJ', 'ADV', 'INTJ', 'AUX']
        #keep_tag = ['VACT','VATT','ADVN','ADVI','ADVP','ADVS','FIXV','NEG','ADJ','']
        pos_list = []
        for sent in pos:
            dt_tags = [t[0] for t in sent if t[1] in keep_tag]
            pos_list.append(dt_tags)


        clean_list = delete_stop(word_list)
        new = tfidf_model.transform(clean_list)
        new = new.toarray()
        new = [n[support] for n in new]

    
        pred = clf_model.predict(new)
        
        my_list = []
        for i in range(len(texts)):
            my_list.append([texts[i], pred[i]])
        return render_template('index.html', tasks = my_list)
        
        

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