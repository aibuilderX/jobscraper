import os
from openai import OpenAI
from .config import Profile
from .models import Job

MODEL = "glm-4.6"
# Z.ai subscription (GLM Coding Plan) uses a different endpoint than pay-as-you-go.
BASE_URL = "https://api.z.ai/api/coding/paas/v4/"

SYSTEM_TMPL = (
    "You are drafting a short freelance pitch. Write 4-5 sentences in the same "
    "language as the job post. Open with one specific detail from the job, state "
    "your approach in one line, propose a concrete timeline, and end with a "
    "question. Plain text, no markdown.\n\n"
    "Freelancer profile: {profile}"
)


def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ["ZAI_API_KEY"], base_url=BASE_URL)


def _profile_for(lang: str, profile: Profile) -> str:
    return {
        "fr": profile.summary_fr,
        "es": profile.summary_es,
    }.get(lang, profile.summary_en)


def draft_pitch(job: Job, profile: Profile, client: OpenAI | None = None) -> str:
    client = client or get_client()
    system = SYSTEM_TMPL.format(profile=_profile_for(job.language, profile))
    user = (
        f"Job title: {job.title}\n"
        f"Job description: {job.description}\n"
        f"Budget (EUR): {job.budget_eur if job.budget_eur is not None else 'not specified'}\n"
        f"Language: {job.language}"
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    return resp.choices[0].message.content.strip()
