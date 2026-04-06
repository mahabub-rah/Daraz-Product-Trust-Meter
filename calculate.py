
from scrape import DarazScraper
from senti import SentimentAnalyzer
from trust import TrustMeter   




url = "https://www.daraz.com.bd/products/-i346571051-s1695895634.html?scm=1007.51610.379274.0&pvid=cedd1a31-63f5-40ce-b703-9598acd03dc4&search=flashsale&spm=a2a0e.tm80335411.FlashSale.d_346571051"



if not url:
    print("Please provide a valid URL.")
    exit(1)
elif "?" in url:
        url = url.split("?")[0]

scraper = DarazScraper(url)
analyzer = SentimentAnalyzer()
trust_meter = TrustMeter()


result = scraper.scrape()
sentiment = analyzer.sentiment_percentage(result["comments"])
trust = trust_meter.calculate_trust_score(
    rating=result["rating"],
    total_reviews=result["total_reviews"],
    sentiment_dict=sentiment
)


print("Title:", result["title"])
print("Price:", result["price"])
print("Rating:", result["rating"])
print("Total Reviews:", result["total_reviews"])
print("Sentiment:", sentiment)
print("Trust Meter:", trust)
