from collections import Counter
from datetime import datetime

import pandas as pd

from app.schemas import CategoryAnalysis, DurationDistribution, KeywordFrequency, VideoDetail


def analyze_category(category_id: str, videos: list[VideoDetail]) -> CategoryAnalysis:
    df = pd.DataFrame([v.model_dump() for v in videos])

    all_words = []
    for title in df["title"]:
        words = [w for w in title.split() if len(w) > 1]
        all_words.extend(words)
    top_keywords = Counter(all_words).most_common(10)
    keywords = [KeywordFrequency(keyword=w, count=c) for w, c in top_keywords]

    hours = [datetime.fromisoformat(p.replace("Z", "+00:00")).hour for p in df["published_at"]]
    avg_upload_hour = round(sum(hours) / len(hours), 1) if hours else 0.0

    avg_duration_seconds = float(df["duration_seconds"].mean())

    short_count = int((df["duration_seconds"] < 240).sum())
    medium_count = int(((df["duration_seconds"] >= 240) & (df["duration_seconds"] <= 1200)).sum())
    long_count = int((df["duration_seconds"] > 1200).sum())
    duration_distribution = DurationDistribution(short=short_count, medium=medium_count, long=long_count)

    thumbnail_urls = df["thumbnail_url"].tolist()

    return CategoryAnalysis(
        category_id=category_id, video_count=len(videos), keywords=keywords,
        avg_upload_hour=avg_upload_hour, avg_duration_seconds=avg_duration_seconds,
        duration_distribution=duration_distribution, thumbnail_urls=thumbnail_urls,
    )
