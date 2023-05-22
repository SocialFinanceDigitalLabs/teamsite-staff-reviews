from reviews.models import Nomination
from reviews.util.word_export.assessment import AssessmentDocument
from reviews.util.word_export.util import add_markdown

questions = [
    "2021 Business Objectives (6-12 month forward view)",
    "2021 Development Goals (6-12 month forward view)",
    "Line manager comments",
    "Employee Comments",
]


class AssessmentDocumentPart2:
    def __init__(self, nomination):
        exclude_questions = [nomination.form.questions.values("pk").last()["pk"]]

        self.__document = ass_doc = AssessmentDocument(
            nomination, exclude_questions=exclude_questions
        )
        document = ass_doc.document
        document.add_page_break()
        document.add_heading("Part 2", 0)
        add_markdown(
            document,
            """
To be complete by line manager and line report **after the moderation meetings** and return
to HR via email no later than Friday 6 August 2021
        """,
        )

        for q in questions:
            document.add_heading(q, level=1)
            add_markdown(
                document,
                """
  * [your response here]
  * [your response here]
  * [your response here]
            """,
                style_name="Small",
            )

    def save(self, filename):
        self.__document.save(filename)
