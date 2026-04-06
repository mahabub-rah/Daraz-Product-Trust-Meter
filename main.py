from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from scrape import DarazScraper
from senti import SentimentAnalyzer
from trust import TrustMeter

app = FastAPI()
templates = Jinja2Templates(directory="templates")


class URLRequest(BaseModel):
    url: str


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
def analyze(payload: URLRequest):
    try:
        url = payload.url.strip()

        if not url:
            return JSONResponse(
                status_code=400,
                content={"error": "Please provide a valid URL."}
            )

        if "?" in url:
            url = url.split("?")[0]

        scraper = DarazScraper(url)
        analyzer = SentimentAnalyzer()
        trust_meter = TrustMeter()

        result = scraper.scrape()

        comments = result.get("comments", [])
        if not comments:
            sentiment = {"positive": 0, "negative": 0, "neutral": 0}
        else:
            sentiment = analyzer.sentiment_percentage(comments)


        trust = trust_meter.calculate_trust_score(
            rating=result["rating"],
            total_reviews=result["total_reviews"],
            sentiment_dict=sentiment
        )


        return {
            "title": result.get("title", ""), 
            "price": result.get("price", 0), 
            "rating": result.get("rating", 0),
            "trust_meter": int(round(trust["trust_score"])),
            "trust_label": trust["trust_label"]
        }

    except Exception as e:
        import traceback
        print("ANALYZE ERROR:")
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )