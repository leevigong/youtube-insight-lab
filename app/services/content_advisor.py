import anthropic

from app.schemas import HotResponse


SYSTEM_PROMPT = """당신은 YouTube 컨텐츠 전략 분석가입니다.
주어진 키워드의 실시간 인기 영상 데이터와 패턴 분석 결과를 바탕으로,
컨텐츠 제작자가 어떤 영상을 만들면 알고리즘의 수혜를 받을 수 있는지 전략 브리핑을 작성합니다.

반드시 아래 형식으로 작성하세요:

## 지금 왜 터지고 있나
(현재 이 키워드에서 조회수가 높은 영상들의 공통 이슈/트렌드 분석)

## 잘 되는 컨텐츠 유형
(상위 영상들의 제목 패턴, 영상 길이, 포맷, 출연자 등 공통점)

## 추천 컨텐츠 전략
(구체적인 컨텐츠 제안 3개 - 제목 예시, 추천 영상 길이, 업로드 시간대, 추천 태그 포함)
"""


def generate_content_strategy(hot_data: HotResponse, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    # hot 데이터를 프롬프트용 텍스트로 변환
    videos_text = "\n".join(
        f"- [{v.video_type}] \"{v.title}\" (채널: {v.channel_title}, "
        f"조회수: {v.view_count:,}, 시간당 조회수: {v.views_per_hour:,.0f}, "
        f"길이: {v.duration_seconds}초, 업로드: {v.published_at}, "
        f"태그: {', '.join(v.tags[:10]) if v.tags else '없음'})"
        for v in hot_data.hot_videos[:15]
    )

    pattern = hot_data.pattern
    pattern_text = (
        f"- 상위 영상 평균 길이: {pattern.avg_duration_seconds:.0f}초 ({pattern.avg_duration_seconds / 60:.1f}분)\n"
        f"- 평균 업로드 시간: {pattern.avg_upload_hour:.1f}시\n"
        f"- 쇼츠 비율: {pattern.shorts_ratio:.0%}\n"
        f"- 제목 키워드: {', '.join(k.keyword for k in pattern.top_title_keywords[:10])}\n"
        f"- 자주 쓰인 태그: {', '.join(t.keyword for t in pattern.common_tags[:10])}"
    )

    user_prompt = (
        f"키워드: \"{hot_data.keyword}\"\n\n"
        f"## 최근 인기 영상 (시간당 조회수 순)\n{videos_text}\n\n"
        f"## 패턴 분석\n{pattern_text}\n\n"
        f"위 데이터를 분석하여 컨텐츠 전략 브리핑을 작성해주세요."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return next(
        (block.text for block in response.content if block.type == "text"),
        "",
    )
