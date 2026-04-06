import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://router.huggingface.co/hf-inference/models/nlptown/bert-base-multilingual-uncased-sentiment"

HEADERS = {
    "Authorization": f"Bearer {os.getenv('HF_TOKEN')}"
}


class SentimentAnalyzer:

    def __init__(self, api_url=API_URL, headers=HEADERS, max_chars=1000):
        self.api_url = api_url
        self.headers = headers
        self.max_chars = max_chars

    def clean_text(self, text):
        """Convert input to safe string and trim extra spaces."""
        if text is None:
            return ""
        return " ".join(str(text).split())

    def truncate_text(self, text):
        """
        Keep text short enough for model input.
        Character-based truncation is a practical safeguard.
        """
        text = self.clean_text(text)
        return text[:self.max_chars]

    def predict(self, text):
        """Predict sentiment for a single text"""

        text = self.truncate_text(text)

        if not text:
            return "neutral"

        data = {"inputs": text}

        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=data,
            timeout=30
        )
        result = response.json()

        if isinstance(result, dict) and "error" in result:
            raise Exception(result["error"])

        predictions = result[0]
        best = max(predictions, key=lambda x: x["score"])

        # Example label: "1 star", "2 stars", "3 stars", ...
        star = int(best["label"][0])

        if star <= 2:
            return "negative"
        elif star == 3:
            return "neutral"
        else:
            return "positive"

    def sentiment_percentage(self, texts):
        """
        Input: list of texts
        Output: percentage of positive, negative, neutral
        """

        labels = []

        for text in texts:
            try:
                label = self.predict(text)
                labels.append(label)
            except Exception as e:
                print(f"Skipped one review due to error: {e}")

        total = len(labels)

        if total == 0:
            return {
                "positive": 0,
                "negative": 0,
                "neutral": 0
            }

        positive = labels.count("positive")
        negative = labels.count("negative")
        neutral = labels.count("neutral")

        return {
            "positive": round((positive / total) * 100, 2),
            "negative": round((negative / total) * 100, 2),
            "neutral": round((neutral / total) * 100, 2)
        }