import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """

        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
            query=environ.get('QUERY_STRING',"")
            params=parse_qs(query)

            reqLocation=params.get("location",[None])[0]
            req_start_date=params.get('start_date',[None])[0]
            req_end_date=params.get('end_date',[None])[0]
            filteredReviews=[]
            if req_start_date:
                    req_start_date = pd.to_datetime(req_start_date, errors='coerce')
            if req_end_date:
                    req_end_date = pd.to_datetime(req_end_date, errors='coerce')
            for review in reviews:
                review_timestamp = pd.to_datetime(review.get("Timestamp"), errors='coerce')
                if ((not req_start_date or req_start_date <= review_timestamp) and
                    (not req_end_date or req_end_date >= review_timestamp) and
                    (not reqLocation or reqLocation == review['Location'])):
                    
                    sentiment_scores = self.analyze_sentiment(review['ReviewBody'])
                    review['sentiment'] = sentiment_scores
                    filteredReviews.append(review)
            
            
            response_body = json.dumps(filteredReviews, indent=2).encode("utf-8")
            
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            VALID_LOCATIONS = {
        'Albuquerque, New Mexico',
        'Carlsbad, California',
        'Chula Vista, California',
        'Colorado Springs, Colorado',
        'Denver, Colorado',
        'El Cajon, California',
        'El Paso, Texas',
        'Escondido, California',
        'Fresno, California',
        'La Mesa, California',
        'Las Vegas, Nevada',
        'Los Angeles, California',
        'Oceanside, California',
        'Phoenix, Arizona',
        'Sacramento, California',
        'Salt Lake City, Utah',
        'San Diego, California',
        'Tucson, Arizona'
    }
            
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            post_data = environ['wsgi.input'].read(content_length).decode('utf-8')
            post_params = parse_qs(post_data)

            review_body = post_params.get('ReviewBody', [None])[0]
            location = post_params.get('Location', [None])[0]

            if not review_body or not location:
                    start_response("400 Bad Request", [("Content-Type", "application/json")])
                    return [b'{"error": "ReviewBody and Location are required"}']
            
            if location not in VALID_LOCATIONS:
                start_response("400 Bad Request", [("Content-Type", "application/json")])
                return [b'{"error": "Invalid location"}']

            
            new_review = {
                "ReviewId": str(uuid.uuid4()),
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ReviewBody": review_body,
                "Location": location
                }
            reviews.append(new_review)

            response_body = json.dumps(new_review, indent=2).encode("utf-8")
            start_response("201 Created", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                ])

            return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()