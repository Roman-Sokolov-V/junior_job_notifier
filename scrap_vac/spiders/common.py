
class MixinCommonSpider():

    @staticmethod
    def _normalize_ws(value: str) -> str:
        """Trim and normalize whitespace to one-line text."""
        return " ".join(value.split()).strip()


    @staticmethod
    def normalize_text(text: str) -> str | None:
        text = text.replace("\n", "").replace("\t", "").strip()
        if text:
            return text
        return None


    @classmethod
    def clean_paragraphs(cls, paragraph_texts: list[str]) -> str:
        return " ".join([
            norm for p in paragraph_texts
            if (norm := cls.normalize_text(p)) is not None
        ])

    @classmethod
    def extract_and_clean_all_text(cls, response, main_block_class: str) -> str:
        paragraphs = response.css(f'.{main_block_class} ::text').getall()
        return  cls.clean_paragraphs(paragraphs)