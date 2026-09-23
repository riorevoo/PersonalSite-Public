"""Services owned by one application, initialized before it accepts traffic."""

from functools import cached_property

from app.core.config import Settings
from app.services.answerer import Answerer, build_answerer
from app.services.knowledge import KnowledgeBase, build_knowledge


class AppServices:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def knowledge(self) -> KnowledgeBase:
        return build_knowledge(self.settings)

    @cached_property
    def answerer(self) -> Answerer:
        return build_answerer(self.settings, self.knowledge)

    def initialize(self) -> None:
        """Fail startup on invalid knowledge and build the engine once for this app."""
        _ = self.knowledge, self.answerer
