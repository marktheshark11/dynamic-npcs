from dataclasses import dataclass


@dataclass
class Form:
    form_id: str
    name: str
    name_en: str | None = None
    description: str | None = None
    description_en: str | None = None

    def display_str(self) -> str:
        return f"ID: {self.form_id}, Namn: {self.name}"

    def short_str(self) -> str:
        return f"{self.form_id}: {self.name}"


@dataclass
class FormQuestion:
    question_id: str
    question: str
    value_type: str
    order: int
    question_en: str | None = None
    scale_min: int | None = None
    scale_max: int | None = None
    min_label: str | None = None
    min_label_en: str | None = None
    max_label: str | None = None
    max_label_en: str | None = None

    def display_str(self) -> str:
        return (
            f"ID: {self.question_id}, Ordning: {self.order}, "
            f"Typ: {self.value_type}, Fraga: {self.question}"
        )

    def short_str(self) -> str:
        return f"{self.order}. {self.question_id} [{self.value_type}]"
