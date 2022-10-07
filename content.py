import pandas as pd
import nltk
nltk.download('stopwords')
nltk.download('punkt')
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.util import bigrams
import random

df = pd.read_csv("Songs.csv")
df['Bigrams'] = df['Artist']
sw = stopwords.words('english')

for row in range(1, len(df)):
    text = df['Lyrics'][row]
    text = word_tokenize(text)
    if text != []:
        text.pop(-1)
        words = [w.lower() for w in text if w.isalpha()]
        clean_lyrics = [w for w in words if w not in sw]
        bigr = set(bigrams(clean_lyrics))
        df['Bigrams'][row] = bigr

def make_question(data):
    n = random.randint(1, len(data))
    keys = ['title', 'artist', 'bigrams']
    to_ask = dict.fromkeys(keys)
    to_ask['title'] = data['Title'][n]
    to_ask['artist'] = data['Artist'][n]
    to_ask['bigrams'] = list(data['Bigrams'][n])
    return(to_ask)

def three_bigrams(question):
    chosen_bigr = []
    for i in range(0,3):
        b = random.choice(question['bigrams'])
        chosen_bigr.append(b)
        question['bigrams'].remove(b)
    return(chosen_bigr)

cur_to_ask = make_question(df)
cur_bigr = three_bigrams(cur_to_ask)
