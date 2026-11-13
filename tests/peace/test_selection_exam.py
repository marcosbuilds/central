from __future__ import annotations

import pytest

from bot.persistence.database import ExamAssignmentExistsError, PeaceDatabase
from bot.main import PeaceBot
from bot.selection import grade_exam, materialize_exam, public_exam_payload


def _perfect_answers(question_order, option_order):
    answers = {}
    for question_id in question_order:
        answers[question_id] = 0
    return answers


def _test_answer_key(question_order, option_order):
    # The test key intentionally marks the first presented option as correct;
    # it does not duplicate the production answer key in the public repository.
    return {question_id: option_order[question_id][0] for question_id in question_order}


def test_materialized_exam_hides_answer_key_and_grades_server_order():
    question_order, option_order = materialize_exam(seed=17)
    payload = public_exam_payload(question_order, option_order)

    assert len(payload) == 10
    assert all("correct_index" not in question for question in payload)
    result = grade_exam(
        _perfect_answers(question_order, option_order),
        question_order,
        option_order,
        _test_answer_key(question_order, option_order),
    )
    assert result["score"] == 100
    assert result["correct_count"] == 10


def test_oauth_state_is_consumed_once(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    database.create_discord_oauth_state(
        state="state-token-123456789012345678901234567890",
        code_verifier="verifier",
        return_to="/meu-processo/",
        expires_at="2030-01-01T00:00:00+00:00",
    )

    consumed = database.consume_discord_oauth_state(
        "state-token-123456789012345678901234567890",
        now="2029-01-01T00:00:00+00:00",
    )
    replay = database.consume_discord_oauth_state(
        "state-token-123456789012345678901234567890",
        now="2029-01-01T00:00:00+00:00",
    )

    assert consumed is not None
    assert consumed["return_to"] == "/meu-processo/"
    assert replay is None


def test_oauth_return_to_rejects_header_injection_and_external_paths():
    assert PeaceBot.public_oauth_return_to("/\r\nLocation: https://evil.example") == "/meu-processo/"
    assert PeaceBot.public_oauth_return_to("//evil.example") == "/meu-processo/"
    assert PeaceBot.public_oauth_return_to("/prova/") == "/prova/"


def test_exam_attempt_and_submission_are_single_use(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    assignment, access_token = database.create_exam_assignment(
        candidate_discord_user_id="12345678901234567",
        candidate_username="candidate",
        manager_discord_user_id="22345678901234567",
        question_bank_version="civil-test",
        passing_score=70,
        deadline_at="2030-01-01T00:00:00+00:00",
    )
    with pytest.raises(ExamAssignmentExistsError):
        database.create_exam_assignment(
            candidate_discord_user_id="12345678901234567",
            candidate_username="candidate",
            manager_discord_user_id="22345678901234567",
            question_bank_version="civil-test",
            passing_score=70,
            deadline_at="2030-01-01T00:00:00+00:00",
        )
    question_order, option_order = materialize_exam(seed=5)
    started, attempt = database.start_exam_attempt(
        assignment_id=assignment["id"],
        candidate_discord_user_id="12345678901234567",
        question_order=question_order,
        option_order=option_order,
        now="2029-01-01T00:00:00+00:00",
    )
    resumed, same_attempt = database.start_exam_attempt(
        assignment_id=assignment["id"],
        candidate_discord_user_id="12345678901234567",
        question_order=list(reversed(question_order)),
        option_order=option_order,
        now="2029-01-01T00:01:00+00:00",
    )
    answers = _perfect_answers(question_order, option_order)
    status, submitted, _ = database.submit_exam_attempt(
        assignment_id=assignment["id"],
        candidate_discord_user_id="12345678901234567",
        answers=answers,
        score=100,
        correct_count=10,
        passed=True,
        now="2029-01-01T00:02:00+00:00",
    )
    replay_status, _, _ = database.submit_exam_attempt(
        assignment_id=assignment["id"],
        candidate_discord_user_id="12345678901234567",
        answers=answers,
        score=0,
        correct_count=0,
        passed=False,
        now="2029-01-01T00:03:00+00:00",
    )

    assert access_token
    assert started["status"] == "in_progress"
    assert resumed["id"] == started["id"]
    assert same_attempt["id"] == attempt["id"]
    assert status == "submitted"
    assert submitted["score"] == 100
    assert replay_status == "already_submitted"
    assert database.candidate_profile("12345678901234567")["score"] == 100


def test_exam_cannot_start_after_deadline(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    assignment, _ = database.create_exam_assignment(
        candidate_discord_user_id="12345678901234567",
        candidate_username="candidate",
        manager_discord_user_id="22345678901234567",
        question_bank_version="civil-test",
        passing_score=70,
        deadline_at="2029-01-01T00:00:00+00:00",
    )
    question_order, option_order = materialize_exam(seed=9)

    expired, attempt = database.start_exam_attempt(
        assignment_id=assignment["id"],
        candidate_discord_user_id="12345678901234567",
        question_order=question_order,
        option_order=option_order,
        now="2029-01-01T00:00:01+00:00",
    )

    assert expired["status"] == "expired"
    assert attempt is None
