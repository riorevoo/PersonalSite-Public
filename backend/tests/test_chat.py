from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.schemas.chat import MAX_HISTORY_TURNS, MAX_TURN_CHARS, ChatTurn
from app.services.answerer import CANNED, FALLBACK, get_answerer
from app.services.errors import EngineUnavailableError
from tests.conftest import RecordingAnswerer


def test_suggestion_gets_canned_answer(client: TestClient) -> None:
    question = next(iter(CANNED))
    response = client.post("/api/chat", json={"message": question.upper()})
    assert response.status_code == 200
    assert response.json() == {"answer": CANNED[question]}


def test_unknown_question_gets_fallback(client: TestClient) -> None:
    response = client.post("/api/chat", json={"message": "what's the weather?"})
    assert response.status_code == 200
    assert response.json()["answer"] == FALLBACK


def test_blank_message_rejected(client: TestClient) -> None:
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422


def test_overlong_message_rejected(client: TestClient) -> None:
    assert client.post("/api/chat", json={"message": "x" * 501}).status_code == 422


def test_engine_is_swappable(client: TestClient, answerer_override: RecordingAnswerer) -> None:
    response = client.post("/api/chat", json={"message": "anything at all"})
    assert response.status_code == 200
    assert response.json() == {"answer": "fake answer"}
    assert [message for message, _ in answerer_override.calls] == ["anything at all"]


def test_history_is_forwarded_to_engine(
    client: TestClient, answerer_override: RecordingAnswerer
) -> None:
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    response = client.post("/api/chat", json={"message": "and now?", "history": history})
    assert response.status_code == 200
    (_, received), *_ = answerer_override.calls
    assert [(turn.role, turn.content) for turn in received] == [
        ("user", "hi"),
        ("assistant", "hello"),
    ]


def test_message_is_trimmed_before_reaching_engine(
    client: TestClient, answerer_override: RecordingAnswerer
) -> None:
    client.post("/api/chat", json={"message": "  padded  "})
    assert answerer_override.calls[0][0] == "padded"


def test_invalid_history_role_rejected(client: TestClient) -> None:
    payload = {"message": "hi", "history": [{"role": "system", "content": "x"}]}
    assert client.post("/api/chat", json=payload).status_code == 422


def test_history_at_the_limit_is_accepted(client: TestClient) -> None:
    history = [{"role": "user", "content": "q"}] * MAX_HISTORY_TURNS
    response = client.post("/api/chat", json={"message": "hi", "history": history})
    assert response.status_code == 200


def test_too_much_history_rejected(client: TestClient) -> None:
    history = [{"role": "user", "content": "q"}] * (MAX_HISTORY_TURNS + 1)
    response = client.post("/api/chat", json={"message": "hi", "history": history})
    assert response.status_code == 422


def test_overlong_history_turn_rejected(client: TestClient) -> None:
    history = [{"role": "assistant", "content": "x" * (MAX_TURN_CHARS + 1)}]
    response = client.post("/api/chat", json={"message": "hi", "history": history})
    assert response.status_code == 422


def test_errors_use_the_detail_shape(client: TestClient) -> None:
    body = client.post("/api/chat", json={"message": "   "}).json()
    assert body == {"detail": "Message is empty."}


class UnavailableAnswerer:
    async def answer(self, message: str, history: list[ChatTurn]) -> str:
        raise EngineUnavailableError("provider said: SECRET DETAIL")


def test_an_unavailable_engine_returns_503_without_leaking_the_cause(
    app: FastAPI, client: TestClient
) -> None:
    app.dependency_overrides[get_answerer] = UnavailableAnswerer

    response = client.post("/api/chat", json={"message": "anything"})

    assert response.status_code == 503
    assert response.json() == {"detail": "The answering service is unavailable right now."}
    assert "SECRET" not in response.text
