from dataclasses import dataclass


@dataclass
class Form:
    form_id: str
    name: str
    name_en: str | None = None

    def display_str(self) -> str:
        return f"ID: {self.form_id}, Namn: {self.name}"

    def short_str(self) -> str:
        return f"{self.form_id}: {self.name}"


@dataclass
class FormQuestion:
    question_id: str
    question: str
    question_en: str | None = None
    value_type: str
    order: int

    def display_str(self) -> str:
        return (
            f"ID: {self.question_id}, Ordning: {self.order}, "
            f"Typ: {self.value_type}, Fraga: {self.question}"
        )

    def short_str(self) -> str:
        return f"{self.order}. {self.question_id} [{self.value_type}]"
