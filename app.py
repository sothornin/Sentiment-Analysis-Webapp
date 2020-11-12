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
# import tempfile
import csv
from flask import send_from_directory
import pygal
from pygal.style import Style

app = Flask(__name__)
app.config['DATASET'] = '/'
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

global top_10

def text_cleaning(texts):
  clean_word = []
  stop_words = thai_stopwords() 
  for text in texts:
    #emoji list
    pos_emoji = re.compile(u'[\U0001F600\U0001F603\U0001F604\U0001F601\U0001F606\U0001F60A\U0000263A\U0000FE0F\U0001F923\U0001F642\U0001F609\U0001F60C\U0001F619\U0001F617\U0001F618\U0001F970\U0001F60D\U0001F61A\U0001F60B\U0001F61B\U0001F61D\U0001F61C\U0001F973\U0001F60F\U0001F633\U0001F638\U0001F63A\U0001F63D\U0001F63B\U0001F63C\U0001F44D\U0001F3FB\U0001F91F\U0001F3FB\U0001F918\U0001F3FB\U0001F48B\U00002764\U0000FE0F\U0001F9E1\U0001F49B\U0001F49A\U0001F499\U0001F49C\U00002763\U0000FE0F\U0001F495\U0001F49E\U0001F493\U0001F497\U0001F496\U0001F498\U0001F49D]',
            flags=re.UNICODE)
    neg_emoji = re.compile(u'[\U0001F494\U0001F642\U0001F643\U0001F61E\U0001F612\U0001F60F\U0001F614\U0001F61F\U0001F615\U0001F641\U00002639\U0000FE0F\U0001F623\U0001F616\U0001F62B\U0001F629\U0001F97A\U0001F622\U0001F62D\U0001F60F\U0001F624\U0001F620\U0001F621\U0001F92C\U0001F92F\U0001F975\U0001F628\U0001F630\U0001F625\U0001F613\U0001F925\U0001F636\U0001F610\U0001F611\U0001F644\U0001F626\U0001F640\U0001F63E\U0001F63C\U0001F595\U0001F3FB\U0001F44E\U0001F3FB\U0001F9B6\U0001F3FB\U0001F448\U0001F3FB\U0001F91E\U0001F3FB\U0001F44B\U0001F3FB\U0001F47F\U0001F47A\U0001F921\U0001F92E\U0001F974\U0001F463]',
            flags=re.UNICODE)
    pos_count = len(re.findall(pos_emoji,text))
    neg_count = len(re.findall(neg_emoji,text))
    #text.replace('☺️', 'posemo')
    #for emo in pos_emoji: text = text.replace(emo,'posemo')

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
    text = emoji_pattern.sub(r"", text)
    #delte Link hashtag and mention
    text = re.sub(r"(?:@\S*|#\S*|http(?=.*://)\S*)", "",text)
    text = re.sub(r"^https://t.co/[A-Za-z0-9]*\s","",text)
    text = re.sub(r"\s+https://t.co/[a-zA-Z0-9]*\s", "", text)
    text = re.sub(r"\s+https://t.co/[a-zA-Z0-9]*$", "", text)
    #find and delete laugh
    laugh_count = len(re.findall(r'(5)\1{2,}(6?){3,}', text))
    text = re.sub(r'(5)\1{2,}(6?){3,}', '', text)
    #delete symbol
    text = re.sub(r'[!-@[-`{-~]',"",text)
    #text = re.sub("\d+", "", text) #number
    text = normalize(text)

    
#Tokenization

    tokens = word_tokenize(text)

#deletion of whitespace & one letter text

    i = 0
    for token in list(tokens):
      if(len(token) == 1 or len(token) == token.count(token[0]) or token in ['xxrep','xxwrep','','ชา','นนท์','ปอนด์','ป้อม']):
        tokens.pop(i)
        i = i-1
      i = i+1

#Add thailaugh posemoji negemoji tag

    for a in range(laugh_count):
      tokens.append('thailaugh')
    for a in range(pos_count):
      tokens.append('posemoji')
    for a in range(neg_count):
      tokens.append('negemoji')
    
# POS Tag

    # from pythainlp.tag import pos_tag
    # pos = pos_tag(tokens,corpus='orchid_ud')
    # keep_tag = ['VERB', 'ADJ', 'ADV', 'INTJ', 'AUX']
    #keep_tag = ['VACT','VATT','ADVN','ADVI','ADVP','ADVS','FIXV','NEG','ADJ','']
    
    
    # pos_tags = [t[0] for t in pos if (t[1] in keep_tag) or (t[0] == "thailaugh") 
    # or (t[0] == "posemoji")  or (t[0] == "negemoji")]
    # tokens = pos_tags

# Delete Stop Word

    filtered_sentence = []
    for t in tokens: 
      if t not in stop_words:
        #t = ''.join(c[0] for c in itertools.groupby(t))
        filtered_sentence.append(t)
    clean_word.append(','.join(filtered_sentence))
  return clean_word


def twitter_trend(api, n):
    trends = api.trends_place(23424960)[0]['trends']
    top_10 = trends[:n]
    trend_list = []
    for trend in top_10:
        trend_list.append(trend['name'])
    #print(trend_list)
    return trend_list
  
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    #completed = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Task %r>' % self.id

@app.route('/',methods=['POST','GET'])
def index():
    tasks = []
    api = tweepy.API(auth,wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    top_10 = twitter_trend(api,10)
    if request.method == 'POST':
        tweet_query = request.form['content']
        tweet_number = int(request.form['number'])
        texts = []
        
        search_words = tweet_query
        new_search = search_words + " -filter:retweets"
        search = tweepy.Cursor(api.search, q=new_search, lang="th", tweet_mode="extended").items(tweet_number)
        texts = [item.full_text for item in search]
        clean_list = text_cleaning(texts)
        #return clean_list[3]
        term_weighting = tfidf_model.transform(clean_list)


        # from pythainlp.tag import pos_tag_sents
        # pos = pos_tag_sents(word_list,corpus='orchid_ud')
        # keep_tag = ['VERB', 'ADJ', 'ADV', 'INTJ', 'AUX']
        # pos_list = []
        # for sent in pos:
        #     dt_tags = [t[0] for t in sent if t[1] in keep_tag]
        #     pos_list.append(dt_tags)


        # clean_list = delete_stop(word_list)
        # new = tfidf_model.transform(clean_list)
        new = term_weighting.toarray()
        new = [n[support] for n in new]
        
    
        pred = clf_model.predict(new)
        #pred = clean_list
        #return pred[1]
        neg_count = 0
        pos_count = 0  
        my_list = []
        with open("dataset.csv", mode='w', newline='', encoding='utf-8') as f:
            thewriter = csv.writer(f)
            thewriter.writerow(["text","sentiment"])
            for i in range(len(texts)):
                my_list.append([texts[i], pred[i]])
                if pred[i] == 1.0:
                    neg_count = neg_count + 1
                    thewriter.writerow([texts[i].replace('\n', ''), 'Negative'])
                else:
                    pos_count = pos_count + 1
                    thewriter.writerow([texts[i].replace('\n', ''), 'Positive'])
        custom_style = Style(colors=('#800000','#3CB371'))
        pie_chart = pygal.Pie(style=custom_style)
        pie_chart.title = 'Sentiment ratio'
        pie_chart.add('Negative', neg_count)
        pie_chart.add('Positive', pos_count)
        
        chart_data = pie_chart.render_data_uri()

        #return str(len(top_10))
        return render_template('index.html', tasks = my_list, trends = top_10, keyword = tweet_query, chart = chart_data)
        
        

    else:
        
        #tasks = Todo.query.order_by(Todo.date_created).all()
        top_10 = twitter_trend(api,10)
        #return top_10[0]
        return render_template('index.html', tasks = [], trends = top_10)

@app.route('/download')
def download():
    return send_from_directory('', filename='dataset.csv', as_attachment=True)
    # csvf = tempfile.TemporaryFile()
    # wr = csv.DictWriter(csvf, fields, encoding = 'cp949')
    # wr.writerow(dict(zip(fields, fields))) #dummy, to explain what each column means
    # for resp in resps :
    #     wr.writerow(resp)
    # wr.close()
    # csvf.seek(0)  # rewind to the start

    # send_file(csvf, as_attachment=True, attachment_filename='survey.csv')


# @app.route('/search/<string:keyword>')
# def search(id):
#     task_to_delete = Todo.query.get_or_404(id)

#     try:
#         db.session.delete(task_to_delete)
#         db.session.commit()
#         return redirect('/')
#     except:
#         return 'There was Error'

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