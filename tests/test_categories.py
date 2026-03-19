import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.routers.categories import get_youtube_service
from app.schemas import Category, CategoriesResponse
from app.services.youtube import YouTubeService


MOCK_CATEGORIES_RESPONSE = {
    "items": [
        {
            "id": "1",
            "snippet": {"title": "Film & Animation", "assignable": True},
        },
        {
            "id": "10",
            "snippet": {"title": "Music", "assignable": True},
        },
        {
            "id": "15",
            "snippet": {"title": "Pets & Animals", "assignable": False},
        },
    ]
}


def test_category_schema():
    cat = Category(id="10", title="Music", assignable=True)
    assert cat.id == "10"
    assert cat.title == "Music"
    assert cat.assignable is True


def test_categories_response_schema():
    resp = CategoriesResponse(
        categories=[
            Category(id="1", title="Film & Animation", assignable=True),
            Category(id="10", title="Music", assignable=True),
        ]
    )
    assert len(resp.categories) == 2
    assert resp.categories[0].id == "1"


def test_get_categories():
    mock_youtube = MagicMock()
    mock_youtube.videoCategories().list().execute.return_value = (
        MOCK_CATEGORIES_RESPONSE
    )

    service = YouTubeService(client=mock_youtube)
    categories = service.get_categories()

    assert len(categories) == 3
    assert categories[0].id == "1"
    assert categories[0].title == "Film & Animation"
    assert categories[0].assignable is True
    assert categories[2].assignable is False


def _mock_youtube_service():
    mock_client = MagicMock()
    mock_client.videoCategories().list().execute.return_value = MOCK_CATEGORIES_RESPONSE
    return YouTubeService(client=mock_client)


@pytest.fixture()
def client():
    app.dependency_overrides[get_youtube_service] = _mock_youtube_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_categories_endpoint(client):
    response = client.get("/categories")

    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert len(data["categories"]) == 3
    assert data["categories"][0]["id"] == "1"
    assert data["categories"][0]["title"] == "Film & Animation"
    assert data["categories"][0]["assignable"] is True
