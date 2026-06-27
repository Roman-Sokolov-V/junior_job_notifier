from dataclasses import dataclass
import csv
from sentence_transformers import SentenceTransformer, util


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

@dataclass
class VacancyRow:
    title: str
    listing_context: str
    description_text: str

    @property
    def full_text(self) -> str:
        parts = [self.title, self.listing_context, self.description_text]
        return "\n".join(part for part in parts if part)

@dataclass
class ProfileRow:
    query_text: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    min_keyword_coverage: float
    min_semantic_score: float
    top_k: int

vacancies = []
with open("gen_tech_ai.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        vacancies.append(
            VacancyRow(
                title=row["title"],
                listing_context=row["listing_context"],
                description_text=row["description_text"],
            )
        )
profiles = [
    ProfileRow(
        query_text="вакансія для новачка, обовязково пайтон, без комерційного або з мінімальним комерційним досвідом. Бекенд, найкраще  Django, Django Rest Framework, Fastapi, також скрапінг. Володію мовами українська, російська як носій, англійська B-1",
        include_keywords=["junior", "intern", "trainee"],
        exclude_keywords=["senior", "middle"],
        min_keyword_coverage=0.2,
        min_semantic_score=0.42,
        top_k=20,
    )
]

def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip().lower()


def to_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def keyword_filter(title: str, full_text: str, include: list[str], exclude: list[str], min_coverage: float) -> tuple[bool, float]:
    # normalization
    norm_title = normalize_text(title)
    norm_text = normalize_text(full_text)

    include_norm = [normalize_text(word) for word in include]
    exclude_norm = [normalize_text(word) for word in exclude]

    # if any word from exclude list in title remove immediately
    if exclude_norm and any(word in norm_title for word in exclude_norm):
        return False, 0.0

    if not include_norm:
        return True, 1.0

    hits = sum(1 for word in include_norm if word in norm_text)
    coverage = hits / len(include_norm)
    return coverage >= min_coverage, coverage


def filter_vacancies(vac: list, profiles: list) -> None:


    model = SentenceTransformer(MODEL_NAME)
    vacancy_texts = [vac.full_text for vac in vacancies]
    vacancy_embeddings = model.encode(vacancy_texts, convert_to_tensor=True)
    total_saved = 0

    for profile in profiles:
        query_embedding = model.encode(profile.query_text, convert_to_tensor=True)
        similarities = util.cos_sim(query_embedding, vacancy_embeddings)[0]

        candidates: list[tuple[int, float, float, float]] = []
        for idx, vacancy in enumerate(vacancies):
            ok, coverage = keyword_filter(
                vacancy.title,
                vacancy.full_text,
                profile.include_keywords,
                profile.exclude_keywords,
                profile.min_keyword_coverage,
            )
            if not ok:
                continue

            semantic = float(similarities[idx])
            if semantic < profile.min_semantic_score:
                continue
            combined = 0.7 * semantic + 0.3 * coverage
            candidates.append((vacancy.id, coverage, semantic, combined))

        candidates.sort(key=lambda row: row[3], reverse=True)
        for vacancy_id, coverage, semantic, combined in candidates[: profile.top_k]:
            save_match(db, profile, vacancy_id, coverage, semantic, combined)
            total_saved += 1

    newest_added_at = max(v.added_at for v in vacancies)
    set_last_run(db, newest_added_at)

    print(f"Processed new vacancies: {len(vacancies)}")
    print(f"Processed active profiles: {len(profiles)}")
    print(f"Saved/updated matches: {total_saved}")
    print(f"Updated state {STATE_KEY} -> {newest_added_at.isoformat()}")

if __name__ == "__main__":
    filter_vacancies(vacancies, profiles)