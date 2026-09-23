from datetime import date
from pathlib import Path

import pytest

from app.schemas.chat import ChatTurn
from app.services.completion import Turn
from app.services.knowledge import KnowledgeBase, load_knowledge
from app.services.prompt import PromptBuilder


@pytest.fixture
def knowledge(tmp_path: Path) -> KnowledgeBase:
    (tmp_path / "profile.md").write_text(
        "---\ntitle: Profile\n---\n\n## Bio\nA bio.\n", encoding="utf-8"
    )
    return load_knowledge(tmp_path)


def turn(role: str, content: str) -> ChatTurn:
    return ChatTurn(role=role, content=content)  # type: ignore[arg-type]


def builder(knowledge: KnowledgeBase, history_turns: int = 6) -> PromptBuilder:
    return PromptBuilder(owner="Ada", knowledge=knowledge, history_turns=history_turns)


class TestSystem:
    def test_names_the_owner_the_persona_and_the_date(self, knowledge: KnowledgeBase) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert "AI answering service on Ada's personal website" in system
        assert 'Refer to Ada as "he" or "Ada"' in system
        assert "Never claim to be Ada" in system
        assert "Today's date is 2026-09-21" in system

    def test_lets_a_broad_projects_question_run_to_two_paragraphs(
        self, knowledge: KnowledgeBase
    ) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert "broad question about his projects" in system
        assert "two short paragraphs" in system

    def test_sets_name_first_voice_and_depth_for_assessments(
        self, knowledge: KnowledgeBase
    ) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert 'use "Ada" in the opening sentence' in system
        assert "Answer simple factual questions briefly" in system
        assert "80 to 130 words" in system
        assert 'lead with the conclusion, normally "Yes, Ada' in system
        assert "two or three strongest relevant examples" in system
        assert "one paragraph" in system

    def test_permits_evidence_backed_assessments_without_inventing_facts(
        self, knowledge: KnowledgeBase
    ) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert "are permitted professional assessments" in system
        assert "A missing explicit verdict is not a missing fact" in system
        assert "keeping the underlying facts and the assessment distinct" in system
        assert "Never guess or invent employers" in system
        assert "learning timelines or guarantees" in system
        assert "I cannot give a personal assessment" in system

    def test_prioritises_relevant_software_and_finance_evidence(
        self, knowledge: KnowledgeBase
    ) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert "For software roles" in system
        assert "development contributions, reliability improvements" in system
        assert "never as the whole of it" in system
        assert "For finance questions" in system
        assert "Finance and FinTech education, quantitative training" in system
        assert "professional finance experience when material" in system

    def test_requires_concrete_transfer_reasoning_and_material_limits(
        self, knowledge: KnowledgeBase
    ) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert "explain the actual technical connection" in system
        assert "Do not merely say that skills are transferable" in system
        assert "Missing experience with one technology does not outweigh" in system
        assert "essential credential, level of seniority or core area" in system
        assert "end on a supported strength or fit" in system

    def test_puts_the_knowledge_in_a_tagged_block(self, knowledge: KnowledgeBase) -> None:
        system = builder(knowledge).system(date(2026, 9, 21))

        assert "<knowledge>\n# Profile" in system
        assert "A bio." in system

    def test_survives_a_missing_boundaries_file(self, knowledge: KnowledgeBase) -> None:
        assert "<boundaries>\n\n</boundaries>" in builder(knowledge).system(date(2026, 9, 21))


class TestTurns:
    def test_ends_with_the_question(self, knowledge: KnowledgeBase) -> None:
        assert builder(knowledge).turns([], "hello?") == [Turn("user", "hello?")]

    def test_keeps_only_the_most_recent_turns(self, knowledge: KnowledgeBase) -> None:
        history = [turn("user" if i % 2 == 0 else "assistant", f"t{i}") for i in range(8)]

        turns = builder(knowledge, history_turns=4).turns(history, "now")

        assert [t.content for t in turns] == ["t4", "t5", "t6", "t7", "now"]

    def test_no_history_when_it_is_switched_off(self, knowledge: KnowledgeBase) -> None:
        history = [turn("user", "a"), turn("assistant", "b")]

        assert builder(knowledge, history_turns=0).turns(history, "q") == [Turn("user", "q")]

    def test_drops_a_leading_assistant_turn_and_empty_turns(self, knowledge: KnowledgeBase) -> None:
        history = [turn("assistant", "orphan"), turn("user", "  "), turn("assistant", "later")]

        assert builder(knowledge).turns(history, "q") == [Turn("user", "q")]

    def test_merges_consecutive_turns_of_the_same_role(self, knowledge: KnowledgeBase) -> None:
        history = [turn("user", "one"), turn("user", "two"), turn("assistant", "reply")]

        turns = builder(knowledge).turns(history, "three")

        assert turns == [
            Turn("user", "one\ntwo"),
            Turn("assistant", "reply"),
            Turn("user", "three"),
        ]
