from .base import BaseRepository
from ..models import Form, FormQuestion


class FormRepo(BaseRepository):
    """CRUD and answer operations for forms and form questions."""

    VALID_VALUE_TYPES = {"string", "int", "bool", "info"}

    def _next_answer_id(self) -> str:
        records = self._run(
            "MATCH (a:FORM_ANSWER) "
            "WHERE a.answer_id IS NOT NULL AND a.answer_id STARTS WITH 'answer_' "
            "RETURN a.answer_id AS answer_id"
        )
        if not records:
            return "answer_1"

        max_num = 0
        for record in records:
            answer_id = record.get("answer_id")
            if not answer_id:
                continue
            suffix = answer_id[7:]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

        return f"answer_{max_num + 1}"

    def _validate_value_type(self, value_type: str) -> str:
        normalized = value_type.strip().lower()
        if normalized not in self.VALID_VALUE_TYPES:
            raise ValueError("value_type must be one of: string, int, bool, info")
        return normalized

    @staticmethod
    def _parse_bool_answer(raw_answer: str, question_id: str) -> tuple[str, bool]:
        normalized = raw_answer.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return "true", True
        if normalized in {"false", "0", "no", "n"}:
            return "false", False
        raise ValueError(f"answer for question_id '{question_id}' must be a boolean")

    @staticmethod
    def _localized_value(locale: str, swedish_value: str | None, english_value: str | None) -> str | None:
        if locale == "en" and english_value:
            return english_value
        return swedish_value

    def create_form(
        self,
        form_id: str,
        name: str,
        name_en: str | None = None,
        description: str | None = None,
        description_en: str | None = None,
    ) -> Form:
        self._run(
            "CREATE (f:FORM {"
            "form_id: $form_id, name: $name, name_en: $name_en, "
            "description: $description, description_en: $description_en"
            "})",
            form_id=form_id,
            name=name,
            name_en=name_en,
            description=description,
            description_en=description_en,
        )
        return Form(
            form_id=form_id,
            name=name,
            name_en=name_en,
            description=description,
            description_en=description_en,
        )

    def list_forms(self) -> list[Form]:
        records = self._run(
            "MATCH (f:FORM) "
            "RETURN f.form_id AS form_id, f.name AS name, f.name_en AS name_en, "
            "f.description AS description, f.description_en AS description_en "
            "ORDER BY f.form_id"
        )
        return [
            Form(
                form_id=r["form_id"],
                name=r["name"],
                name_en=r.get("name_en"),
                description=r.get("description"),
                description_en=r.get("description_en"),
            )
            for r in records
        ]

    def get_form(self, form_id: str, locale: str = "sv") -> dict | None:
        record = self._run_single(
            "MATCH (f:FORM {form_id: $form_id}) "
            "RETURN f.form_id AS form_id, f.name AS name, f.name_en AS name_en, "
            "f.description AS description, f.description_en AS description_en",
            form_id=form_id,
        )
        if not record:
            return None
        questions = self.list_form_questions(form_id, locale=locale)
        return {
            "form_id": record["form_id"],
            "name": self._localized_value(locale, record.get("name"), record.get("name_en")),
            "description": self._localized_value(
                locale,
                record.get("description"),
                record.get("description_en"),
            ),
            "questions": [
                {
                    "question_id": question.question_id,
                    "question": question.question,
                    "value_type": question.value_type,
                    "order": question.order,
                    "required": question.required,
                    "scale_min": question.scale_min,
                    "scale_max": question.scale_max,
                    "min_label": question.min_label,
                    "max_label": question.max_label,
                }
                for question in questions
            ],
        }

    def add_question(
        self,
        form_id: str,
        question_id: str,
        question: str,
        question_en: str | None,
        value_type: str,
        order: int,
        required: bool = True,
        scale_min: int | None = None,
        scale_max: int | None = None,
        min_label: str | None = None,
        min_label_en: str | None = None,
        max_label: str | None = None,
        max_label_en: str | None = None,
    ) -> FormQuestion:
        normalized_type = self._validate_value_type(value_type)
        if normalized_type == "int":
            if scale_min is None or scale_max is None:
                raise ValueError("scale_min and scale_max are required for int questions")
            if scale_min > scale_max:
                raise ValueError("scale_min cannot be greater than scale_max")
        elif any(value is not None for value in (scale_min, scale_max, min_label, min_label_en, max_label, max_label_en)):
            raise ValueError("scale fields are only supported for int questions")

        if normalized_type == "info":
            required = False

        record = self._run_single(
            "MATCH (f:FORM {form_id: $form_id}) "
            "CREATE (q:FORM_QUESTION {"
            "question_id: $question_id, question: $question, question_en: $question_en, value_type: $value_type, `order`: $order, required: $required, "
            "scale_min: $scale_min, scale_max: $scale_max, min_label: $min_label, min_label_en: $min_label_en, "
            "max_label: $max_label, max_label_en: $max_label_en"
            "}) "
            "CREATE (f)-[:HAS_QUESTION]->(q) "
            "RETURN q.question_id AS question_id",
            form_id=form_id,
            question_id=question_id,
            question=question,
            question_en=question_en,
            value_type=normalized_type,
            order=order,
            required=required,
            scale_min=scale_min,
            scale_max=scale_max,
            min_label=min_label,
            min_label_en=min_label_en,
            max_label=max_label,
            max_label_en=max_label_en,
        )
        if not record:
            raise ValueError("Form not found")
        return FormQuestion(
            question_id=question_id,
            question=question,
            question_en=question_en,
            value_type=normalized_type,
            order=order,
            required=required,
            scale_min=scale_min,
            scale_max=scale_max,
            min_label=min_label,
            min_label_en=min_label_en,
            max_label=max_label,
            max_label_en=max_label_en,
        )

    def list_form_questions(self, form_id: str, locale: str = "sv") -> list[FormQuestion]:
        records = self._run(
            "MATCH (f:FORM {form_id: $form_id})-[:HAS_QUESTION]->(q:FORM_QUESTION) "
            "RETURN q.question_id AS question_id, q.question AS question, q.question_en AS question_en, "
            "q.value_type AS value_type, q.`order` AS order, q.required AS required, q.scale_min AS scale_min, q.scale_max AS scale_max, "
            "q.min_label AS min_label, q.min_label_en AS min_label_en, q.max_label AS max_label, q.max_label_en AS max_label_en "
            "ORDER BY q.`order`, q.question_id",
            form_id=form_id,
        )
        return [
            FormQuestion(
                question_id=r["question_id"],
                question=self._localized_value(locale, r.get("question"), r.get("question_en")) or "",
                question_en=r.get("question_en"),
                value_type=r["value_type"],
                order=int(r["order"]),
                required=bool(r.get("required")) if r.get("required") is not None else True,
                scale_min=r.get("scale_min"),
                scale_max=r.get("scale_max"),
                min_label=self._localized_value(locale, r.get("min_label"), r.get("min_label_en")),
                min_label_en=r.get("min_label_en"),
                max_label=self._localized_value(locale, r.get("max_label"), r.get("max_label_en")),
                max_label_en=r.get("max_label_en"),
            )
            for r in records
        ]

    def get_player_form_answers(self, player_id: str, form_id: str, locale: str = "sv") -> dict | None:
        form_data = self.get_form(form_id, locale=locale)
        if not form_data:
            return None

        records = self._run(
            "MATCH (p:PLAYER {player_id: $player_id})-[:HAS_FORM_ANSWER]->(a:FORM_ANSWER)<-[:HAS_ANSWER]-(q:FORM_QUESTION)<-[:HAS_QUESTION]-(f:FORM {form_id: $form_id}) "
            "RETURN q.question_id AS question_id, a.raw_answer AS raw_answer, a.answer_bool AS answer_bool "
            "ORDER BY q.`order`, q.question_id",
            player_id=player_id,
            form_id=form_id,
        )
        answer_by_question = {
            r["question_id"]: {
                "answer": r.get("raw_answer"),
                "answer_bool": r.get("answer_bool"),
            }
            for r in records
        }
        return {
            "form_id": form_data["form_id"],
            "name": form_data["name"],
            "description": form_data.get("description"),
            "questions": [
                {
                    **question,
                    "answer": (answer_by_question.get(question["question_id"]) or {}).get("answer"),
                    "answer_bool": (answer_by_question.get(question["question_id"]) or {}).get("answer_bool"),
                }
                for question in form_data["questions"]
            ],
        }

    def list_player_forms_with_answers(self, player_id: str, locale: str = "sv") -> list[dict]:
        records = self._run(
            "MATCH (p:PLAYER {player_id: $player_id})-[:HAS_FORM_ANSWER]->(a:FORM_ANSWER)<-[:HAS_ANSWER]-(q:FORM_QUESTION)<-[:HAS_QUESTION]-(f:FORM) "
            "RETURN f.form_id AS form_id, f.name AS form_name, f.name_en AS form_name_en, "
            "f.description AS form_description, f.description_en AS form_description_en, "
            "q.question_id AS question_id, q.question AS question, q.question_en AS question_en, "
            "q.value_type AS value_type, q.`order` AS question_order, "
            "a.raw_answer AS raw_answer, a.answer_text AS answer_text, a.answer_int AS answer_int, a.answer_bool AS answer_bool "
            "ORDER BY f.form_id, q.`order`, q.question_id",
            player_id=player_id,
        )

        forms_by_id: dict[str, dict] = {}
        for record in records:
            form_id = record["form_id"]
            form_entry = forms_by_id.setdefault(
                form_id,
                {
                    "form_id": form_id,
                    "name": self._localized_value(locale, record.get("form_name"), record.get("form_name_en")),
                    "description": self._localized_value(
                        locale,
                        record.get("form_description"),
                        record.get("form_description_en"),
                    ),
                    "answers": [],
                },
            )
            form_entry["answers"].append(
                {
                    "question_id": record["question_id"],
                    "question": self._localized_value(locale, record.get("question"), record.get("question_en")),
                    "value_type": record["value_type"],
                    "order": int(record.get("question_order") or 0),
                    "raw_answer": record.get("raw_answer"),
                    "answer_text": record.get("answer_text"),
                    "answer_int": record.get("answer_int"),
                    "answer_bool": record.get("answer_bool"),
                }
            )

        return list(forms_by_id.values())

    def save_player_form_answers(self, player_id: str, form_id: str, answers: list[dict]) -> list[dict]:
        player_record = self._run_single(
            "MATCH (p:PLAYER {player_id: $player_id}) RETURN p.player_id AS player_id",
            player_id=player_id,
        )
        if not player_record:
            raise ValueError("Player not found")

        questions = self.list_form_questions(form_id)
        if not questions:
            form_exists = self._run_single(
                "MATCH (f:FORM {form_id: $form_id}) RETURN f.form_id AS form_id",
                form_id=form_id,
            )
            if not form_exists:
                raise ValueError("Form not found")
            raise ValueError("Form has no questions")

        question_by_id = {question.question_id: question for question in questions}
        submitted_ids = [str(item.get("question_id", "")).strip() for item in answers]

        if len(submitted_ids) != len(set(submitted_ids)):
            raise ValueError("Duplicate question_id values are not allowed")

        answerable_ids = {
            question.question_id
            for question in questions
            if question.value_type != "info"
        }
        required_ids = {
            question.question_id
            for question in questions
            if question.value_type != "info" and question.required
        }
        actual_ids = set(submitted_ids)

        if not actual_ids.issubset(answerable_ids) or required_ids - actual_ids:
            missing = sorted(required_ids - actual_ids)
            extra = sorted(actual_ids - answerable_ids)
            details = []
            if missing:
                details.append(f"missing question_ids: {', '.join(missing)}")
            if extra:
                details.append(f"non-answerable or unknown question_ids: {', '.join(extra)}")
            raise ValueError("All required form questions must be answered; " + "; ".join(details))

        saved_answers = []
        for item in answers:
            question_id = str(item.get("question_id", "")).strip()
            raw_answer = str(item.get("answer", "")).strip()
            if not question_id:
                raise ValueError("question_id cannot be empty")
            if raw_answer == "":
                raise ValueError(f"answer cannot be empty for question_id '{question_id}'")

            question = question_by_id[question_id]
            answer_text: str | None = None
            answer_int: int | None = None
            answer_bool: bool | None = None

            if question.value_type == "string":
                answer_text = raw_answer
            elif question.value_type == "int":
                try:
                    answer_int = int(raw_answer)
                except ValueError as exc:
                    raise ValueError(
                        f"answer for question_id '{question_id}' must be an integer"
                    ) from exc
                if question.scale_min is not None and answer_int < question.scale_min:
                    raise ValueError(
                        f"answer for question_id '{question_id}' must be >= {question.scale_min}"
                    )
                if question.scale_max is not None and answer_int > question.scale_max:
                    raise ValueError(
                        f"answer for question_id '{question_id}' must be <= {question.scale_max}"
                    )
            elif question.value_type == "bool":
                raw_answer, answer_bool = self._parse_bool_answer(raw_answer, question_id)
            else:
                raise ValueError(f"Unsupported value_type '{question.value_type}'")

            existing = self._run_single(
                "MATCH (p:PLAYER {player_id: $player_id})-[:HAS_FORM_ANSWER]->(a:FORM_ANSWER)<-[:HAS_ANSWER]-(q:FORM_QUESTION {question_id: $question_id}) "
                "RETURN a.answer_id AS answer_id",
                player_id=player_id,
                question_id=question_id,
            )

            if existing:
                answer_id = existing["answer_id"]
                self._run(
                    "MATCH (a:FORM_ANSWER {answer_id: $answer_id}) "
                    "SET a.raw_answer = $raw_answer, a.value_type = $value_type, "
                    "a.answer_text = $answer_text, a.answer_int = $answer_int, a.answer_bool = $answer_bool",
                    answer_id=answer_id,
                    raw_answer=raw_answer,
                    value_type=question.value_type,
                    answer_text=answer_text,
                    answer_int=answer_int,
                    answer_bool=answer_bool,
                )
            else:
                answer_id = self._next_answer_id()
                self._run(
                    "MATCH (p:PLAYER {player_id: $player_id}) "
                    "MATCH (q:FORM_QUESTION {question_id: $question_id}) "
                    "CREATE (a:FORM_ANSWER {"
                    "answer_id: $answer_id, raw_answer: $raw_answer, value_type: $value_type, "
                    "answer_text: $answer_text, answer_int: $answer_int, answer_bool: $answer_bool, created_at: datetime()"
                    "}) "
                    "CREATE (p)-[:HAS_FORM_ANSWER]->(a) "
                    "CREATE (q)-[:HAS_ANSWER]->(a)",
                    player_id=player_id,
                    question_id=question_id,
                    answer_id=answer_id,
                    raw_answer=raw_answer,
                    value_type=question.value_type,
                    answer_text=answer_text,
                    answer_int=answer_int,
                    answer_bool=answer_bool,
                )

            saved_answers.append(
                {
                    "question_id": question_id,
                    "value_type": question.value_type,
                    "raw_answer": raw_answer,
                    "answer_bool": answer_bool,
                }
            )

        saved_answers.sort(key=lambda item: question_by_id[item["question_id"]].order)
        return saved_answers
