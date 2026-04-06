import math


class TrustMeter:
    """
    Create a trust score for a product using only available data:
    - rating
    - total reviews
    - sentiment distribution from comments

    Final trust score is scaled to 0-100.
    """

    def __init__(self, w_rating=0.45, w_sentiment=0.35, w_reviews=0.20):
        total = w_rating + w_sentiment + w_reviews
        self.w_rating = w_rating / total
        self.w_sentiment = w_sentiment / total
        self.w_reviews = w_reviews / total

    def _safe_float(self, value, default=0.0):
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return default
            return float(value)
        except:
            return default

    def _safe_int(self, value, default=0):
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.strip().replace(",", "")
                if not value:
                    return default
            return int(float(value))
        except:
            return default

    def normalize_rating(self, rating):
        """
        Normalize rating from 0-5 scale to 0-1 scale.
        """
        rating = self._safe_float(rating, 0.0)
        rating = max(0.0, min(rating, 5.0))
        return rating / 5.0

    def review_confidence(self, total_reviews):
        """
        Confidence increases with review volume.
        Caps at 1.0 after enough reviews.

        You can tune the denominator:
        - 100 => faster confidence growth
        - 500 => medium
        - 1000 => slower, stricter
        """
        total_reviews = self._safe_int(total_reviews, 0)

        # log-based scaling gives smoother growth
        # 0 reviews => 0
        # 10 reviews => moderate
        # 100+ reviews => high
        if total_reviews <= 0:
            return 0.0

        confidence = math.log1p(total_reviews) / math.log1p(1000)
        return min(confidence, 1.0)

    def sentiment_score(self, sentiment_dict):
        """
        Convert sentiment percentage/count dictionary into score [0,1].

        Expected possible keys:
        - positive / neutral / negative
        - POSITIVE / NEUTRAL / NEGATIVE
        - LABEL_0 / LABEL_1 / LABEL_2  (depending on model output)

        Scoring:
        positive = 1.0
        neutral  = 0.5
        negative = 0.0
        """
        if not sentiment_dict or not isinstance(sentiment_dict, dict):
            return 0.5  # neutral fallback

        # support multiple naming styles
        positive = (
            sentiment_dict.get("positive", 0)
            or sentiment_dict.get("POSITIVE", 0)
            or sentiment_dict.get("LABEL_2", 0)
        )

        neutral = (
            sentiment_dict.get("neutral", 0)
            or sentiment_dict.get("NEUTRAL", 0)
            or sentiment_dict.get("LABEL_1", 0)
        )

        negative = (
            sentiment_dict.get("negative", 0)
            or sentiment_dict.get("NEGATIVE", 0)
            or sentiment_dict.get("LABEL_0", 0)
        )

        positive = self._safe_float(positive, 0.0)
        neutral = self._safe_float(neutral, 0.0)
        negative = self._safe_float(negative, 0.0)

        total = positive + neutral + negative
        if total == 0:
            return 0.5  # fallback neutral

        score = (positive * 1.0 + neutral * 0.5 + negative * 0.0) / total
        return max(0.0, min(score, 1.0))

    def calculate_trust_score(self, rating, total_reviews, sentiment_dict):
        """
        Return detailed trust score breakdown.
        Final score is out of 100.
        """
        rating_score = self.normalize_rating(rating)
        sentiment_score = self.sentiment_score(sentiment_dict)
        review_score = self.review_confidence(total_reviews)

        final_score_0_1 = (
            self.w_rating * rating_score +
            self.w_sentiment * sentiment_score +
            self.w_reviews * review_score
        )

        final_score_0_100 = round(final_score_0_1 * 100, 2)

        return {
            "trust_score": final_score_0_100,
            "trust_label": self.trust_label(final_score_0_100)
        }

    def trust_label(self, score):
        """
        Human-readable label for the trust meter.
        """
        if score >= 85:
            return "Excellent Trust"
        elif score >= 70:
            return "High Trust"
        elif score >= 55:
            return "Moderate Trust"
        elif score >= 40:
            return "Low Trust"
        else:
            return "Risky / Uncertain"
        
"""

"""