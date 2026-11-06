from __future__ import annotations

import re
from collections.abc import Iterable


MENTION_RE = re.compile(r"<@!?\d{15,22}>|<@&\d{15,22}>|<#\d{15,22}>")
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
SECRET_RE = re.compile(
    r"(?i)\b(?:token|senha|password|authorization|bearer|api[_ -]?key)\b\s*[:=]?\s*\S+"
)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\s().-]?){8,16}(?!\d)")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
SNOWFLAKE_RE = re.compile(r"(?<!\d)\d{15,22}(?!\d)")
CODE_BLOCK_RE = re.compile(r"```(?:json|xml|python|javascript|text)?\s*[\s\S]*?```", re.IGNORECASE)
XML_BLOCK_RE = re.compile(r"<(?:svg|script|style)\b[\s\S]*?</(?:svg|script|style)>", re.IGNORECASE)
XML_TAG_RE = re.compile(r"\\?</?(?:svg|script|style)\b[^>]*>", re.IGNORECASE)
GENERIC_SUPPORT_LINE_RE = re.compile(r"(?im)^\s*\*{0,2}se precisar da equipe, mencione a staff\.?\*{0,2}\.?\s*$")
INTERNAL_LINE_MARKERS = (
    "contexto interno",
    "contexto organizacional",
    "mensagens recentes do ticket",
    "perfil operacional",
    "organization_context",
    "iris_system",
    "metadata_json",
    "needs_details",
    "destructive",
    '"action":',
    '"subject":',
    '"needs_details":',
    '"destructive":',
    "json",
    "system:",
    "assistant:",
    "developer:",
    "ignore previous",
    "ignore instruções",
    "qwen",
    "ollama",
    "provedor",
    "modelo local",
    "inteligência artificial",
    "seja direta e faça no máximo",
    "faça no máximo uma pergunta",
    "responda agora ao último ponto relevante",
    "só mencione",
    "[referência interna]",
    "[dado sensível removido]",
    "se necessário, mencione a staff",
)


def redact(value: str, *, limit: int = 1200) -> str:
    """Remove identificadores e segredos antes de qualquer contexto chegar à Iris."""
    text = str(value or "").replace("\x00", " ").strip()
    text = SECRET_RE.sub("[dado sensível removido]", text)
    text = EMAIL_RE.sub("[e-mail removido]", text)
    text = URL_RE.sub("[link removido]", text)
    text = MENTION_RE.sub("[referência interna]", text)
    text = PHONE_RE.sub("[número removido]", text)
    text = SNOWFLAKE_RE.sub("[id interno removido]", text)
    return re.sub(r"\s+", " ", text)[:limit]


def message_lines(messages: Iterable[object], *, role_resolver=None, limit: int = 1200) -> list[str]:
    lines: list[str] = []
    for message in messages:
        content = redact(getattr(message, "content", ""), limit=limit)
        if not content and getattr(message, "attachments", None):
            content = "[anexo omitido]"
        if not content:
            continue
        author = role_resolver(message) if role_resolver else "participante"
        lines.append(f"{author}: {content}")
    return lines


def bounded_context(parts: Iterable[str], *, limit: int = 12000) -> str:
    text = "\n".join(part for part in parts if part)
    return text[-limit:]


def sanitize_assistant_output(value: str, *, forbidden_context: str = "", limit: int = 1800) -> str:
    """Aplica uma barreira final antes de qualquer texto da Iris chegar ao Discord."""
    text = str(value or "").replace("\x00", " ").strip()
    text = CODE_BLOCK_RE.sub("", text)
    text = XML_BLOCK_RE.sub("", text)
    text = XML_TAG_RE.sub("", text)
    text = GENERIC_SUPPORT_LINE_RE.sub("", text)
    safe_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not any(marker in line.casefold() for marker in INTERNAL_LINE_MARKERS)
    ]
    text = "\n".join(safe_lines).strip()
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        text = ""
    text = redact(text, limit=limit)
    answer_folded = text.casefold()
    private_fragments = [
        line.strip()
        for line in str(forbidden_context or "").splitlines()
        if len(line.strip()) >= 40 and not line.lstrip().startswith("[")
    ]
    if any(fragment.casefold() in answer_folded for fragment in private_fragments):
        text = ""
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Posso ajudar com isso, mas preciso de mais uma informação para continuar."


def concise_assistant_output(value: str, *, interview: bool = False, limit: int = 1100) -> str:
    """Aplica o limite de linguagem simples depois da resposta do modelo."""
    text = re.sub(r"(?i)^entendi que você quer[^.!?]*[.!?]\s*", "", str(value or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    if interview:
        question = text.find("?")
        if question >= 0:
            text = text[: question + 1]
        sentences = re.split(r"(?<=[.!?])\s+", text)
        internal_markers = (
            "histórico", "historico", "perfil", "score", "entrou no servidor",
            "contribuições reais", "contribuicoes reais", "contexto interno",
        )
        if len(sentences) > 1:
            sentences = [
                sentence for index, sentence in enumerate(sentences)
                if index == len(sentences) - 1
                or not any(marker in sentence.casefold() for marker in internal_markers)
            ]
            text = " ".join(sentences)
        if len(sentences) > 2:
            question_index = next((index for index, sentence in enumerate(sentences) if "?" in sentence), 1)
            text = " ".join(sentences[: question_index + 1])
    if len(text) > limit:
        shortened = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:")
        text = shortened + ("..." if shortened else "")
    return text or "Posso fazer uma pergunta simples para continuar?"
