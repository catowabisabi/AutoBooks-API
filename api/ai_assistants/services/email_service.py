"""AI helpers for Email Assistant."""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Tuple

from django.conf import settings
from openai import OpenAI

from ai_assistants.models import Email

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
	api_key = getattr(settings, "OPENAI_API_KEY", None)
	if not api_key:
		raise RuntimeError("OPENAI_API_KEY is not configured")
	return OpenAI(api_key=api_key)


def summarize_email(email: Email) -> Dict[str, object]:
	"""Generate AI summary, action items, and sentiment for an email."""
	prompt = (
		"You are an email analysis assistant for an accounting and audit firm. "
		"Summarize the email in 2 sentences, extract up to 3 actionable next steps "
		"with deadlines if mentioned, and label the sentiment as positive, neutral, or negative. "
		"Respond in JSON with keys: summary (string), action_items (array of {action, deadline}), sentiment (string)."
	)

	body = email.body_text or email.body_html or ""
	email_context = (
		f"From: {email.from_name or ''} <{email.from_address}>\n"
		f"To: {', '.join(email.to_addresses or [])}\n"
		f"Subject: {email.subject}\n"
		f"Body: {body[:4000]}"
	)

	try:
		client = _get_client()
		completion = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=[
				{"role": "system", "content": prompt},
				{"role": "user", "content": email_context},
			],
			response_format={"type": "json_object"},
			temperature=0.2,
			max_tokens=500,
		)
		raw_content = completion.choices[0].message.content or "{}"
		data = json.loads(raw_content)
	except RuntimeError as exc:
		logger.warning("Email summary skipped: %s", exc)
		return {
			"summary": "AI summarization unavailable (missing API key).",
			"action_items": [],
			"sentiment": "neutral",
		}
	except Exception as exc:  # pragma: no cover - defensive logging
		logger.error("Email summary failed: %s", exc, exc_info=True)
		raise

	return {
		"summary": data.get("summary") or "No summary provided.",
		"action_items": data.get("action_items") or [],
		"sentiment": data.get("sentiment") or "neutral",
	}


def generate_ai_reply(email: Email, tone: str = "professional", key_points: List[str] | None = None) -> Dict[str, str]:
	"""Generate an AI-crafted reply for an email."""
	key_points = key_points or []
	body = email.body_text or email.body_html or ""

	system_prompt = (
		"You are a helpful email drafting assistant for a professional services firm. "
		"Write a concise reply in the requested tone. Maintain a polite greeting and closing."
	)

	user_prompt = (
		f"Tone: {tone}\n"
		f"Key points to include: {', '.join(key_points) if key_points else 'N/A'}\n"
		f"From: {email.from_name or ''} <{email.from_address}>\n"
		f"Subject: {email.subject}\n"
		f"Body: {body[:4000]}"
	)

	try:
		client = _get_client()
		completion = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			temperature=0.4,
			max_tokens=500,
		)
		reply_text = (completion.choices[0].message.content or "").strip()
	except RuntimeError as exc:
		logger.warning("Email reply generation skipped: %s", exc)
		reply_text = (
			"Unable to generate an AI reply because no AI provider is configured. "
			"Please set OPENAI_API_KEY."
		)
	except Exception as exc:  # pragma: no cover - defensive logging
		logger.error("Email reply generation failed: %s", exc, exc_info=True)
		raise

	return {"suggested_reply": reply_text, "tone": tone}
