from __future__ import annotations

from enum import Enum


class GatherTab(str, Enum):
    CHAT = "chat"
    FACTS = "facts"
    SLOTS = "slots"
    QUESTIONS = "questions"
    DOCUMENT = "document"
    EXPORT = "export"


GATHER_TAB_ORDER: list[GatherTab] = [
    GatherTab.CHAT,
    GatherTab.FACTS,
    GatherTab.SLOTS,
    GatherTab.QUESTIONS,
    GatherTab.DOCUMENT,
    GatherTab.EXPORT,
]

TAB_LABELS: dict[GatherTab, str] = {
    GatherTab.CHAT: "Chat",
    GatherTab.FACTS: "Facts",
    GatherTab.SLOTS: "Slots",
    GatherTab.QUESTIONS: "Questions",
    GatherTab.DOCUMENT: "Document",
    GatherTab.EXPORT: "Export",
}
