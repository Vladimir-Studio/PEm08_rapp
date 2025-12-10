import json
from pathlib import Path

from backend.config import settings


class HistoryService:
    def __init__(self):
        self.file = Path(settings.history_file)
        if not self.file.exists():
            self.file.write_text("[]", encoding="utf-8")

    def add_entry(self, request_type: str, request_summary: str, response_summary: str):
        data = self.get_history()
        data.insert(
            0,
            {
                "request_type": request_type,
                "request_summary": request_summary,
                "response_summary": response_summary,
            },
        )
        data = data[: settings.max_history_items]
        self.file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_history(self):
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def clear_history(self):
        self.file.write_text("[]", encoding="utf-8")


history_service = HistoryService()

