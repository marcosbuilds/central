"""Versioned, server-side question bank and grading for the Civil intake exam.

The public browser receives only the materialized prompt and option order. The
answer key and the source mapping stay in this module so a candidate cannot
grade or rewrite an attempt from the client.
"""

from __future__ import annotations

import random
import secrets
import json
from dataclasses import dataclass
from typing import Any, Mapping


CIVIL_BANK_VERSION = "civil-2026-11-13"
CIVIL_SCORE_SCALE = 100
CIVIL_DEFAULT_PASSING_SCORE = 70


@dataclass(frozen=True)
class CivilQuestion:
    question_id: str
    category: str
    prompt: str
    options: tuple[str, ...]
    source_pages: tuple[str, ...]
    context: str = ""
    points: int = 10


CIVIL_QUESTION_BANK: tuple[CivilQuestion, ...] = (
    CivilQuestion(
        question_id="civil-general-01",
        category="general",
        prompt="Uma modulação precisa ser clara para que a equipe consiga agir. Qual conjunto reúne as informações essenciais indicadas no material?",
        options=(
            "Apenas o nome de quem fala e a opinião de quem está comunicando.",
            "Quem fala, o que ocorreu, onde ocorreu e o que é necessário.",
            "Somente o código operacional e uma estimativa do resultado.",
            "O histórico completo da equipe, sem necessidade de localização.",
        ),
        source_pages=("material-civil:p6",),
    ),
    CivilQuestion(
        question_id="civil-general-02",
        category="general",
        prompt="Durante uma comunicação de rotina, a equipe precisa informar a localização. Qual referência do Código Q corresponde a esse uso?",
        options=(
            "QAP.",
            "QSL.",
            "QTH.",
            "QRT.",
        ),
        source_pages=("material-civil:p7",),
    ),
    CivilQuestion(
        question_id="civil-general-03",
        category="general",
        prompt="Uma pessoa decide permanecer em silêncio durante uma abordagem. Qual conduta é compatível com os direitos apresentados no material?",
        options=(
            "Pressionar a pessoa até que ela responda para encerrar o atendimento.",
            "Desconsiderar o silêncio e registrar qualquer versão como confissão.",
            "Respeitar o silêncio e seguir o procedimento, preservando a integridade e a informação verificável.",
            "Impedir assistência jurídica para evitar interferência na apuração.",
        ),
        source_pages=("material-civil:p9",),
    ),
    CivilQuestion(
        question_id="civil-general-04",
        category="general",
        prompt="Ao receber uma informação sobre uma ocorrência, qual é a melhor sequência inicial para evitar que uma hipótese seja tratada como fato?",
        options=(
            "Publicar a primeira versão e verificar somente depois.",
            "Receber o relato, verificar, separar fatos de suposições e levantar dados relevantes.",
            "Escolher a versão mais grave e iniciar o relatório pelo resultado.",
            "Ignorar registros anteriores para manter a apuração imparcial.",
        ),
        source_pages=("material-civil:p10",),
    ),
    CivilQuestion(
        question_id="civil-general-05",
        category="general",
        prompt="Qual conjunto corresponde ao modelo simples de relatório apresentado no material?",
        options=(
            "Opinião, suspeita, punição e encerramento.",
            "Fato, ação, resultado e encaminhamento.",
            "Rumor, denúncia, julgamento e divulgação.",
            "Local, cargo, suspeito e sentença.",
        ),
        source_pages=("material-civil:p12",),
    ),
    CivilQuestion(
        question_id="civil-general-06",
        category="general",
        prompt="No manual de convivência da Peace, participar não significa concordar com tudo. Qual atitude melhor traduz essa ideia?",
        options=(
            "Evitar qualquer opinião para não assumir responsabilidade.",
            "Discordar com respeito, ouvir outras pessoas e contribuir para construir uma solução.",
            "Impor a própria posição sempre que houver divergência.",
            "Transferir toda decisão para outra pessoa, mesmo quando puder ajudar.",
        ),
        source_pages=("a-peace:p5",),
    ),
    CivilQuestion(
        question_id="civil-investigation-01",
        category="investigation",
        prompt="Qual é a decisão mais responsável para iniciar a análise de um relatório de inteligência com vídeos, perfis públicos e pessoas identificadas?",
        context=(
            "Caso prático anonimizado: uma equipe encaminha quatro registros audiovisuais e aponta possíveis integrantes de uma organização. "
            "O relatório registra prisões e perfis públicos, mas ainda é necessário confirmar a autenticidade, o vínculo de cada pessoa e o que cada evidência demonstra."
        ),
        options=(
            "Tratar todas as alegações do relatório como fatos provados e divulgar a conclusão.",
            "Descartar os registros porque nenhum material isolado pode ser útil.",
            "Preservar os registros, separar fatos de hipóteses, verificar as identidades e comparar as versões antes de concluir.",
            "Escolher a pessoa mais citada como responsável e buscar apenas elementos que confirmem essa hipótese.",
        ),
        source_pages=("material-civil:p10", "material-civil:p12", "relatorio-anonimizado"),
    ),
    CivilQuestion(
        question_id="civil-investigation-02",
        category="investigation",
        prompt="Durante uma entrevista investigativa, qual pergunta é mais adequada para começar a esclarecer um relato sem forçar uma resposta?",
        options=(
            "Você confirma exatamente a versão que já foi publicada?",
            "O que aconteceu naquele momento?",
            "Por que você decidiu esconder a informação?",
            "Quem deve ser punido antes de ouvirmos outras pessoas?",
        ),
        source_pages=("material-civil:p11",),
    ),
    CivilQuestion(
        question_id="civil-patrol-01",
        category="patrol",
        prompt="Qual sequência acompanha o fluxo de patrulhamento apresentado no material?",
        options=(
            "Patrulhar, perceber, comunicar, avaliar, apoiar quando necessário e encerrar registrando o resultado.",
            "Encerrar, comunicar, patrulhar, publicar o resultado e depois avaliar.",
            "Apoiar primeiro, escolher a hipótese e só então observar o ambiente.",
            "Avaliar somente depois de encerrar e dispensar a comunicação à Central.",
        ),
        source_pages=("material-civil:p13",),
    ),
    CivilQuestion(
        question_id="civil-patrol-02",
        category="patrol",
        prompt="Ao atender uma ocorrência, qual conduta organiza o antes, o durante e o depois?",
        options=(
            "Conhecer o chamado e o local; comunicar mudanças e pedir auxílio preciso; confirmar o desfecho e registrar.",
            "Chegar sem entender o chamado; manter silêncio durante a ocorrência; encerrar sem registro.",
            "Registrar apenas a opinião da equipe e dispensar a confirmação do desfecho.",
            "Pedir auxílio sem informar localização e deixar o resultado para outra equipe.",
        ),
        source_pages=("material-civil:p14",),
    ),
)


def _random_source(seed: int | None = None) -> random.Random | secrets.SystemRandom:
    return random.Random(seed) if seed is not None else secrets.SystemRandom()


def materialize_exam(seed: int | None = None) -> tuple[list[str], dict[str, list[int]]]:
    """Return a question order and a private canonical-index map for an attempt."""
    source = _random_source(seed)
    question_order = [question.question_id for question in CIVIL_QUESTION_BANK]
    source.shuffle(question_order)
    option_order: dict[str, list[int]] = {}
    for question in CIVIL_QUESTION_BANK:
        indices = list(range(len(question.options)))
        source.shuffle(indices)
        option_order[question.question_id] = indices
    return question_order, option_order


def public_question_payload(question: CivilQuestion, option_order: list[int]) -> dict[str, Any]:
    return {
        "id": question.question_id,
        "category": question.category,
        "prompt": question.prompt,
        "context": question.context,
        "options": [question.options[index] for index in option_order],
        "points": question.points,
    }


def public_exam_payload(question_order: list[str], option_order: Mapping[str, list[int]]) -> list[dict[str, Any]]:
    questions_by_id = {question.question_id: question for question in CIVIL_QUESTION_BANK}
    return [
        public_question_payload(questions_by_id[question_id], list(option_order[question_id]))
        for question_id in question_order
    ]


def parse_answer_key(raw: str | Mapping[str, Any]) -> dict[str, int]:
    """Parse the private answer key supplied by the runtime environment.

    The answer key is deliberately not part of the public question-bank module.
    Production supplies a compact JSON object through a protected environment
    variable; tests may pass a mapping directly without committing real answers.
    """
    if isinstance(raw, Mapping):
        payload: Any = raw
    else:
        if not raw or len(raw) > 4096:
            raise ValueError("answer key is missing or too large")
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("answer key is not valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("answer key must be an object")
    expected_ids = {question.question_id for question in CIVIL_QUESTION_BANK}
    if {str(key) for key in payload} != expected_ids:
        raise ValueError("answer key does not match the question bank")
    questions_by_id = {question.question_id: question for question in CIVIL_QUESTION_BANK}
    answer_key: dict[str, int] = {}
    for question_id in expected_ids:
        value = payload.get(question_id)
        if isinstance(value, bool):
            raise ValueError("answer key contains a boolean index")
        try:
            canonical_index = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("answer key contains an invalid index") from exc
        if not 0 <= canonical_index < len(questions_by_id[question_id].options):
            raise ValueError("answer key contains an out-of-range index")
        answer_key[question_id] = canonical_index
    return answer_key


def grade_exam(
    answers: Mapping[str, Any],
    question_order: list[str],
    option_order: Mapping[str, list[int]],
    answer_key: Mapping[str, int],
) -> dict[str, Any]:
    """Grade exactly one materialized exam, rejecting missing or extra answers."""
    expected_ids = set(question_order)
    received_ids = {str(key) for key in answers}
    if received_ids != expected_ids:
        missing = sorted(expected_ids - received_ids)
        extra = sorted(received_ids - expected_ids)
        raise ValueError(f"answers must match the materialized exam; missing={missing}; extra={extra}")

    if set(answer_key) != expected_ids:
        raise ValueError("answer key must match the materialized exam")

    questions_by_id = {question.question_id: question for question in CIVIL_QUESTION_BANK}
    correct_count = 0
    score = 0
    correct_ids: list[str] = []
    for question_id in question_order:
        question = questions_by_id[question_id]
        try:
            presented_index = int(answers[question_id])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"invalid answer for {question_id}") from exc
        presented_options = option_order.get(question_id, [])
        if not 0 <= presented_index < len(presented_options):
            raise ValueError(f"invalid option for {question_id}")
        if presented_options[presented_index] == int(answer_key[question_id]):
            correct_count += 1
            score += question.points
            correct_ids.append(question_id)

    return {
        "score": score,
        "scale": CIVIL_SCORE_SCALE,
        "correct_count": correct_count,
        "total_questions": len(question_order),
        "correct_ids": correct_ids,
        "distribution": {"general": 60, "investigation": 20, "patrol": 20},
    }

