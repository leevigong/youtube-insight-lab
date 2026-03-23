from app.services.youtube import detect_video_type


def test_shorts_by_duration():
    assert detect_video_type(60, "일반 제목", []) == "shorts"
    assert detect_video_type(30, "짧은 영상", []) == "shorts"
    assert detect_video_type(1, "매우 짧은 영상", []) == "shorts"


def test_regular_by_duration():
    assert detect_video_type(61, "일반 영상", []) == "regular"
    assert detect_video_type(300, "5분 영상", []) == "regular"


def test_shorts_by_title_hashtag():
    assert detect_video_type(120, "재밌는 영상 #shorts", []) == "shorts"
    assert detect_video_type(300, "#Shorts 챌린지", []) == "shorts"


def test_shorts_by_tag_hashtag():
    assert detect_video_type(120, "일반 제목", ["#shorts"]) == "shorts"
    assert detect_video_type(300, "일반 제목", ["음악", "#Shorts"]) == "shorts"


def test_regular_without_shorts_indicator():
    assert detect_video_type(120, "일반 동영상 제목", ["음악", "팝"]) == "regular"


def test_shorts_hashtag_case_insensitive():
    assert detect_video_type(120, "영상 #SHORTS", []) == "shorts"
    assert detect_video_type(120, "영상 #ShOrTs", []) == "shorts"
