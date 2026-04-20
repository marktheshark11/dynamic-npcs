from .base import Command
from ..models import Form, FormQuestion
from ..repositories import FormRepo
from ..ui import InputHelpers


class CreateFormCommand(Command):
    def __init__(self, repo: FormRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Skapa ett formulär"

    def execute(self) -> None:
        form_id = self._ui.prompt("form_id")
        name = self._ui.prompt("namn")
        name_en = self._ui.prompt_optional("namn pa engelska")
        description = self._ui.prompt_optional("beskrivning")
        description_en = self._ui.prompt_optional("beskrivning pa engelska")
        if not form_id:
            self._ui.display.error("form_id far inte vara tomt")
            return
        if not name:
            self._ui.display.error("namn far inte vara tomt")
            return

        form = self._repo.create_form(
            form_id,
            name,
            name_en=name_en,
            description=description,
            description_en=description_en,
        )
        self._ui.display.success(f"FORM '{form.form_id}' skapad")


class ListFormsCommand(Command):
    def __init__(self, repo: FormRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa alla formulär"

    def execute(self) -> None:
        forms = self._repo.list_forms()
        if not forms:
            self._ui.display.error("Inga formulär hittades")
            return

        self._ui.display.header("Alla formulär")
        self._ui.display.list_items(forms, Form.display_str)


class CreateFormQuestionCommand(Command):
    def __init__(self, repo: FormRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Lagg till fraga i formulär"

    def execute(self) -> None:
        forms = self._repo.list_forms()
        selected_form = self._ui.select_from_list(forms, Form.display_str, "Valj formulär")
        if not selected_form:
            return

        question_id = self._ui.prompt("question_id")
        question = self._ui.prompt("fraga")
        question_en = self._ui.prompt_optional("fraga pa engelska")
        value_type = self._ui.select_option(["string", "int", "bool", "info"], "Valj value_type")
        if not value_type:
            return
        order = self._ui.prompt_int("ordning")
        required = False if value_type == "info" else self._ui.confirm("Ar fragan obligatorisk?")
        scale_min = None
        scale_max = None
        min_label = None
        min_label_en = None
        max_label = None
        max_label_en = None
        if value_type == "int":
            scale_min = self._ui.prompt_int("skala min")
            scale_max = self._ui.prompt_int("skala max")
            min_label = self._ui.prompt_optional("min etikett")
            min_label_en = self._ui.prompt_optional("min etikett pa engelska")
            max_label = self._ui.prompt_optional("max etikett")
            max_label_en = self._ui.prompt_optional("max etikett pa engelska")

        if not question_id:
            self._ui.display.error("question_id far inte vara tomt")
            return
        if not question:
            self._ui.display.error("fraga far inte vara tom")
            return

        try:
            form_question = self._repo.add_question(
                selected_form.form_id,
                question_id,
                question,
                question_en,
                value_type,
                order,
                required,
                scale_min,
                scale_max,
                min_label,
                min_label_en,
                max_label,
                max_label_en,
            )
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return

        self._ui.display.success(f"Fraga '{form_question.question_id}' tillagd i '{selected_form.form_id}'")


class EditFormQuestionCommand(Command):
    def __init__(self, repo: FormRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Redigera formulärfråga"

    def execute(self) -> None:
        forms = self._repo.list_forms()
        selected_form = self._ui.select_from_list(forms, Form.display_str, "Välj formulär")
        if not selected_form:
            return

        questions = self._repo.list_form_questions(selected_form.form_id)
        selected_question = self._ui.select_from_list(
            questions,
            FormQuestion.display_str,
            "Välj fråga",
        )
        if not selected_question:
            return

        question = self._ui.prompt_optional("fråga")
        question_en = self._ui.prompt_optional("fråga på engelska")
        value_type_option = self._ui.select_option(
            ["ingen ändring", "string", "int", "bool", "info"],
            "Välj value_type",
        )
        if value_type_option is None:
            return
        value_type = None if value_type_option == "ingen ändring" else value_type_option

        order = self._ui.prompt_optional_int("ordning")
        required: bool | None = None
        selected_value_type = value_type or selected_question.value_type
        if selected_value_type != "info":
            required_option = self._ui.select_option(
                ["ingen ändring", "ja", "nej"],
                "Är frågan obligatorisk?",
            )
            if required_option is None:
                return
            if required_option == "ja":
                required = True
            elif required_option == "nej":
                required = False

        scale_min = None
        scale_max = None
        min_label = None
        min_label_en = None
        max_label = None
        max_label_en = None
        if selected_value_type == "int":
            scale_min = self._ui.prompt_optional_int("skala min")
            scale_max = self._ui.prompt_optional_int("skala max")
            min_label = self._ui.prompt_optional("min etikett")
            min_label_en = self._ui.prompt_optional("min etikett på engelska")
            max_label = self._ui.prompt_optional("max etikett")
            max_label_en = self._ui.prompt_optional("max etikett på engelska")

        try:
            updated = self._repo.update_question(
                form_id=selected_form.form_id,
                question_id=selected_question.question_id,
                question=question,
                question_en=question_en,
                value_type=value_type,
                order=order,
                required=required,
                scale_min=scale_min,
                scale_max=scale_max,
                min_label=min_label,
                min_label_en=min_label_en,
                max_label=max_label,
                max_label_en=max_label_en,
            )
        except ValueError as exc:
            self._ui.display.error(str(exc))
            return

        if updated:
            self._ui.display.success(
                f"Fråga '{selected_question.question_id}' uppdaterad i '{selected_form.form_id}'"
            )
        else:
            self._ui.display.error("Kunde inte uppdatera frågan")


class ListFormQuestionsCommand(Command):
    def __init__(self, repo: FormRepo, ui: InputHelpers) -> None:
        self._repo = repo
        self._ui = ui

    @property
    def name(self) -> str:
        return "Visa formulärfrågor"

    def execute(self) -> None:
        forms = self._repo.list_forms()
        selected_form = self._ui.select_from_list(forms, Form.display_str, "Valj formulär")
        if not selected_form:
            return

        questions = self._repo.list_form_questions(selected_form.form_id)
        if not questions:
            self._ui.display.error(f"Inga frågor hittades för '{selected_form.form_id}'")
            return

        self._ui.display.header(f"Frågor i '{selected_form.form_id}'")
        self._ui.display.list_items(questions, FormQuestion.display_str)
