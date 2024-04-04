import mysql.connector
from flask import Flask, render_template, request, jsonify
import spacy
from nltk.corpus import wordnet as wn
import enchant
import requests

english_dict = enchant.Dict("en_US")
app2 = Flask(__name__)

nlp = spacy.load("en_core_web_sm")

GOOGLE_API_KEY = "AIzaSyA0yAYyLIn62oFKVFRpKWTaT8MtV5IGMw8"
GOOGLE_CX = "25c552550cb7041ce"

def connect_to_database():
    try:
        connection = mysql.connector.connect( 
            host="localhost",
            user="root",
            password="admin",
            database="chatbotdb"
        )
        return connection
    except mysql.connector.Error as err:
        print("Error:", err)

def get_synonyms(word):
    synonyms = set()
    for synset in wn.synsets(word):
        for lemma in synset.lemmas():
            synonyms.add(lemma.name())
    return list(synonyms)

def preprocess_input(input_text):
    doc = nlp(input_text.lower())
    no_stop_words = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    preprocessed_text = ' '.join(no_stop_words)
    return preprocessed_text

def expand_synonyms(text):
    words = text.split()
    expanded_text = []
    for word in words:
        synonyms = get_synonyms(word)
        expanded_text.append(word)
        expanded_text.extend(synonyms)
    return ' '.join(expanded_text)

def correct_spelling(input_text):
    corrected_words = []
    words = input_text.split()
    for word in words:
        if english_dict.check(word):
            corrected_words.append(word)
        else:
            suggestions = english_dict.suggest(word)
            if suggestions:
                corrected_words.append(suggestions[0])
            else:
                corrected_words.append(word)
    
    return ' '.join(corrected_words)

def search_web(query):
    search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CX}&q={query}"
    response = requests.get(search_url).json()
    if 'items' in response:
        first_result = response['items'][0]
        return {
            "name": first_result['title'],
            "url": first_result['link'],
            "description": first_result['snippet']
        }
    else:
        return None

def get_last_id(cursor):
    query = "SELECT MAX(cbid) FROM chatbots"
    cursor.execute(query)
    last_id = cursor.fetchone()[0]
    if last_id is not None:
        return last_id
    else:
        return 0

@app2.route("/chat", methods=["POST"])
def fetch_chatbot_info():
    try:
        connection = connect_to_database()
        if connection:
            cursor = connection.cursor()
            user_message = request.json.get("message")
            
            corrected_message = correct_spelling(user_message)
            preprocessed_message = preprocess_input(corrected_message)
            expanded_message = expand_synonyms(preprocessed_message)

            query = "SELECT * FROM chatbots WHERE MATCH(name, description) AGAINST (%s IN NATURAL LANGUAGE MODE)"
            cursor.execute(query, (expanded_message,))
            records = cursor.fetchall()
            if records:
                response = {
                    "name": records[0][1],
                    "url": records[0][2],
                    "description": records[0][3]
                }
                response["url"] = f"<a href='{response['url']}' target='_blank'>{response['url']}</a>"
            else:
                # Search the web
                web_result = search_web(user_message)
                if web_result:
                    last_id = get_last_id(cursor)
                    new_id = last_id + 1
                    # If a result is found, add it to the database
                    query = "INSERT INTO chatbots (cbid, name, url, description) VALUES (%s, %s, %s, %s)"
                    cursor.execute(query, (new_id, web_result['name'], web_result['url'], web_result['description']))
                    connection.commit()
                    response = {
                        "name": web_result['name'],
                        "url": web_result['url'],
                        "description": web_result['description']
                    }
                    response["url"] = f"<a href='{response['url']}'  target='_blank'>{response['url']}</a>"
                else:
                    response = {
                        "name": "Not Found",
                        "url": "Not Found",
                        "description": "Sorry, I couldn't find any relevant information. Please check your query."
                    }
                        
            cursor.close()
            connection.close()
            return jsonify(response)
    except mysql.connector.Error as err:
        print("Error:", err)

@app2.route("/")
def index2():
    return render_template("index2.html")

if __name__ == "__main__":
    app2.run(debug=True)




'''
CX ID: 25c552550cb7041ce
Google API: AIzaSyA0yAYyLIn62oFKVFRpKWTaT8MtV5IGMw8
'''