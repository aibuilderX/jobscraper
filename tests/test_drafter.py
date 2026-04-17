from unittest.mock import MagicMock
from jobscraper.drafter import draft_pitch
from jobscraper.config import Profile


def _fake_client(reply: str) -> MagicMock:
    c = MagicMock()
    c.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=reply))
    ]
    return c


def test_draft_pitch_returns_reply_text(job_factory):
    profile = Profile(summary_en="EN profile", summary_fr="FR profile", summary_es="ES profile")
    job = job_factory(language="en")
    client = _fake_client("Hello, here is my pitch.")
    out = draft_pitch(job, profile, client=client)
    assert out == "Hello, here is my pitch."


def test_draft_pitch_uses_fr_profile_for_fr_job(job_factory):
    profile = Profile(summary_en="EN profile", summary_fr="FR profile", summary_es="ES profile")
    job = job_factory(language="fr", title="Besoin d'une landing page",
                      description="Site vitrine Next.js")
    client = _fake_client("Bonjour, voici mon offre.")
    draft_pitch(job, profile, client=client)
    call = client.chat.completions.create.call_args
    assert "FR profile" in call.kwargs["messages"][0]["content"]


def test_draft_pitch_uses_es_profile_for_es_job(job_factory):
    profile = Profile(summary_en="EN profile", summary_fr="FR profile", summary_es="ES profile")
    job = job_factory(language="es")
    client = _fake_client("Hola.")
    draft_pitch(job, profile, client=client)
    call = client.chat.completions.create.call_args
    assert "ES profile" in call.kwargs["messages"][0]["content"]
