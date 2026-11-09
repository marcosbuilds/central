import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.main import (
    PeaceBot,
    VerificationCaptchaSelect,
    VerificationStartView,
    needs_visitor,
    render_captcha_png,
    reviewer_member,
    role_member,
    staff_member,
    verification_eligible,
)


def member(member_id, roles=(), *, bot=False):
    return SimpleNamespace(
        id=member_id,
        roles=[SimpleNamespace(id=role_id) for role_id in roles],
        bot=bot,
    )


def test_only_human_without_peace_or_visitor_needs_verification():
    assert needs_visitor(member(10), 200, 400)
    assert needs_visitor(member(10, [300]), 200, 400)
    assert not needs_visitor(member(10, [400]), 200, 400)


def test_peace_members_and_bots_do_not_need_visitor():
    assert not needs_visitor(member(10, [200]), 200)
    assert not needs_visitor(member(11, bot=True), 200)


def test_role_member_and_staff_guard_are_access_based():
    staff = member(20, [500])
    founder = member(1)
    ordinary = member(30, [600])
    settings = SimpleNamespace(founder_user_id=1, staff_role_id=500)

    assert role_member(staff, 500)
    assert staff_member(staff, settings)
    assert staff_member(founder, settings)
    assert not staff_member(ordinary, settings)


def test_reviewers_are_staff_or_management_not_recruiter_labels():
    settings = SimpleNamespace(founder_user_id=1, staff_role_id=500, manager_role_id=700)

    assert reviewer_member(member(20, [500]), settings)
    assert reviewer_member(member(21, [700]), settings)
    assert not reviewer_member(member(22, [800]), settings)


def test_verification_eligibility_excludes_bots_peace_and_existing_visitor():
    assert verification_eligible(member(10), 200, 400)
    assert verification_eligible(member(10, [500]), 200, 400, 500)
    assert not verification_eligible(member(10), 200, 400, 500)
    assert not verification_eligible(member(11, [200]), 200, 400)
    assert not verification_eligible(member(12, [400]), 200, 400)
    assert not verification_eligible(member(13, bot=True), 200, 400)


def test_verification_challenge_contains_one_answer_and_expires(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
    )
    bot = PeaceBot(settings)

    choices = bot.create_verification_challenge(10)
    answer, expires_at = bot.verification_challenges[10]

    assert len(choices) == 5
    assert len(set(choices)) == 5
    assert answer in choices
    assert expires_at > 0


def test_captcha_is_rendered_as_a_png_without_plain_text_answer():
    image = render_captcha_png("ABC234")

    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"ABC234" not in image


def test_verification_panel_has_banner_steps_and_explanation_card():
    embeds = PeaceBot.verification_panel_embeds()
    banner, explanation = embeds

    assert banner.title == "◈ Verificação de acesso"
    assert banner.description is None
    assert [field.name for field in banner.fields] == [
        "1 · INICIAR",
        "2 · LER",
        "3 · SELECIONAR",
    ]
    assert all(field.inline for field in banner.fields)
    assert banner.image.url == "attachment://verification.png"
    assert explanation.title == "Como funciona"
    assert "cargo **Visitor**" in explanation.description
    assert {field.name for field in explanation.fields} == {"O que faz", "Por que existe"}


def test_set_panel_keeps_explanation_below_the_banner_without_status_block(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        set_vagas_abertas=True,
        developer_vagas_abertas=False,
        staff_vagas_abertas=False,
    )
    bot = PeaceBot(settings)

    banner, details = bot.set_panel_embeds()

    assert banner.image.url == "attachment://set.png"
    assert [field.name for field in banner.fields] == [
        "1 · ESCOLHER",
        "2 · PREENCHER",
        "3 · ANALISAR",
    ]
    assert details.title == "Como funciona"
    assert [field.name for field in details.fields] == ["Regra"]
    rendered_details = " ".join(
        [details.description or "", *(field.name for field in details.fields), *(field.value for field in details.fields)]
    )
    assert "Disponibilidade" not in rendered_details
    assert "Player set: OPEN" not in rendered_details
    assert "Join Developers: CLOSED" not in rendered_details
    assert "Join Staff: CLOSED" not in rendered_details
    assert "Uma nova entrada de Player" in details.fields[0].value


def test_support_panel_uses_banner_and_explanation_card():
    banner, details = PeaceBot.support_panel_embeds()

    assert banner.title == "◈ Atendimento Peace"
    assert banner.image.url == "attachment://support.png"
    assert [field.name for field in banner.fields] == [
        "1 · ESCOLHER",
        "2 · DESCREVER",
        "3 · ACOMPANHAR",
    ]
    assert details.title == "Como funciona"
    assert [field.name for field in details.fields] == ["O que faz", "Por que existe"]


def test_operations_panel_uses_banner_and_explanation_card():
    banner, details = PeaceBot.operations_panel_embeds()

    assert banner.title == "◷ Operações Peace"
    assert banner.image.url == "attachment://ops.png"
    assert [field.name for field in banner.fields] == [
        "1 · INICIAR",
        "2 · ACOMPANHAR",
        "3 · FINALIZAR",
    ]
    assert details.title == "Como funciona"
    assert [field.name for field in details.fields] == ["O que faz", "Por que existe"]


def test_welcome_panel_uses_banner_and_explanation_card():
    banner, details = PeaceBot.welcome_panel_embeds()

    assert banner.title == "◈ Bem-vindo à Peace"
    assert banner.image.url == "attachment://welcome.png"
    assert [field.name for field in banner.fields] == [
        "1 · LER",
        "2 · ENTRAR",
        "3 · FALAR",
    ]
    assert details.title == "Como funciona"
    assert [field.name for field in details.fields] == ["O que faz", "Por que existe"]


def test_log_card_uses_actor_thumbnail_and_vertical_fields():
    actor = SimpleNamespace(
        display_avatar=SimpleNamespace(url="https://cdn.example.test/avatar.png"),
    )

    embed = PeaceBot.log_card(
        "Ponto iniciado",
        actor=actor,
        fields=(("Usuário", "@F⎰ Montenegro 0"), ("Horário", "quarta-feira")),
    )

    assert embed.title == "Ponto iniciado"
    assert embed.thumbnail.url == "https://cdn.example.test/avatar.png"
    assert [field.name for field in embed.fields] == ["Usuário", "Horário"]
    assert all(not field.inline for field in embed.fields)
    assert embed.footer.text == "Peace · logs"


def test_send_log_routes_embed_to_configured_log_channel(tmp_path):
    log_channel_id = 987654321012345678
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        log_channel_id=log_channel_id,
    )
    bot = PeaceBot(settings)
    bot.send_to_channel = AsyncMock()

    asyncio.run(
        bot.send_log(
            "Ponto iniciado",
            fields=(("Usuário", "@member"),),
        )
    )

    bot.send_to_channel.assert_awaited_once()
    args, kwargs = bot.send_to_channel.await_args
    assert args == (log_channel_id,)
    assert "content" not in kwargs
    assert kwargs["embed"].title == "Ponto iniciado"


def test_spam_control_panel_has_no_legacy_branding_or_markup():
    embed = PeaceBot.automod_embed()
    rendered = " ".join(
        [
            embed.title or "",
            embed.description or "",
            *(field.name for field in embed.fields),
            *(field.value for field in embed.fields),
        ]
    ).casefold()

    assert "peace // spam control" not in rendered
    assert "contenção automática" not in rendered
    assert PeaceBot.is_automod_panel_message(
        SimpleNamespace(content="**PEACE // SPAM CONTROL**", embeds=[], attachments=[])
    )
    assert PeaceBot.is_automod_panel_message(
        SimpleNamespace(content="", embeds=[embed], attachments=[])
    )


def test_verification_button_defers_and_returns_ephemeral_captcha_image(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400, name="Visitor")
    not_verified = SimpleNamespace(id=500, name="Not Verified")
    guild = SimpleNamespace(
        get_role=lambda role_id: {visitor.id: visitor, not_verified.id: not_verified}.get(role_id),
        roles=[visitor, not_verified],
    )
    member = MagicMock(spec=discord.Member)
    member.id = 10
    member.bot = False
    member.roles = [not_verified]
    member.guild = guild
    interaction = SimpleNamespace(
        user=member,
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
    )
    view = VerificationStartView(bot)

    asyncio.run(view.children[0].callback(interaction))

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    kwargs = interaction.edit_original_response.await_args.kwargs
    answer = bot.verification_challenges[member.id][0]
    captcha_file = kwargs["attachments"][0]
    captcha_file.fp.seek(0)
    assert captcha_file.filename == "captcha.png"
    assert captcha_file.fp.read(8) == b"\x89PNG\r\n\x1a\n"
    assert answer not in kwargs["content"]
    assert kwargs["embed"].image.url == "attachment://captcha.png"


def test_wrong_captcha_keeps_visitor_unassigned_and_offers_retry(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400, name="Visitor", managed=False)
    not_verified = SimpleNamespace(id=500, name="Not Verified", managed=False)
    guild = SimpleNamespace(
        get_role=lambda role_id: {400: visitor, 500: not_verified}.get(role_id),
        roles=[visitor, not_verified],
    )
    member = MagicMock(spec=discord.Member)
    member.id = 10
    member.bot = False
    member.roles = [not_verified]
    member.guild = guild
    interaction = SimpleNamespace(
        user=member,
        guild=guild,
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
    )
    bot.verification_challenges[member.id] = ("ABC234", time.monotonic() + 180)
    select = VerificationCaptchaSelect(bot, member.id, ["ABC234", "WRONG"])
    select._values = ["WRONG"]

    asyncio.run(select.callback(interaction))

    interaction.response.defer.assert_awaited_once_with()
    assert member.id not in bot.verification_challenges
    member.add_roles.assert_not_awaited()
    member.remove_roles.assert_not_awaited()
    kwargs = interaction.edit_original_response.await_args.kwargs
    assert "tentar novamente" in kwargs["content"]
    assert isinstance(kwargs["view"], VerificationStartView)


def test_correct_captcha_grants_visitor_and_removes_not_verified(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)

    class FakeRole:
        def __init__(self, role_id, name):
            self.id = role_id
            self.name = name
            self.managed = False

        def __ge__(self, other):
            return False

    visitor = FakeRole(400, "Visitor")
    not_verified = FakeRole(500, "Not Verified")
    bot_role = FakeRole(900, "PeaceBot")
    guild = SimpleNamespace(
        get_role=lambda role_id: {400: visitor, 500: not_verified}.get(role_id),
        roles=[visitor, not_verified, bot_role],
        me=SimpleNamespace(top_role=bot_role),
    )
    member = MagicMock(spec=discord.Member)
    member.id = 10
    member.bot = False
    member.roles = [not_verified]
    member.guild = guild
    member.add_roles = AsyncMock()
    member.remove_roles = AsyncMock()
    interaction = SimpleNamespace(
        user=member,
        guild=guild,
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
    )
    bot.verification_challenges[member.id] = ("ABC234", time.monotonic() + 180)
    select = VerificationCaptchaSelect(bot, member.id, ["ABC234", "WRONG"])
    select._values = ["ABC234"]

    asyncio.run(select.callback(interaction))

    member.add_roles.assert_awaited_once_with(visitor, reason="CAPTCHA de verificação concluído")
    member.remove_roles.assert_awaited_once_with(not_verified, reason="CAPTCHA de verificação concluído")
    assert "liberei o cargo Visitor" in interaction.edit_original_response.await_args.kwargs["content"]


def test_reconcile_never_grants_visitor_without_captcha(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400)
    guild = SimpleNamespace(get_role=lambda role_id: visitor)
    human = SimpleNamespace(
        id=10,
        bot=False,
        roles=[SimpleNamespace(id=700)],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )

    asyncio.run(bot.reconcile_visitor_role(human))

    human.add_roles.assert_not_awaited()
    human.remove_roles.assert_not_awaited()


def test_reconcile_assigns_not_verified_to_a_new_human(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400)
    not_verified = SimpleNamespace(id=500)
    guild = SimpleNamespace(
        get_role=lambda role_id: {400: visitor, 500: not_verified}.get(role_id),
        roles=[visitor, not_verified, SimpleNamespace(id=700)],
    )
    human = SimpleNamespace(
        id=10,
        bot=False,
        roles=[],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )

    asyncio.run(bot.reconcile_visitor_role(human))

    human.add_roles.assert_awaited_once_with(
        not_verified,
        reason="Entrada exige verificação antes de Visitor",
    )
    human.remove_roles.assert_not_awaited()


def test_reconcile_removes_not_verified_after_visitor_or_peace(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400)
    not_verified = SimpleNamespace(id=500)
    peace = SimpleNamespace(id=200)
    guild = SimpleNamespace(
        get_role=lambda role_id: {200: peace, 400: visitor, 500: not_verified}.get(role_id),
        roles=[peace, visitor, not_verified],
    )
    verified = SimpleNamespace(
        id=10,
        bot=False,
        roles=[visitor, not_verified],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )
    peace_member = SimpleNamespace(
        id=11,
        bot=False,
        roles=[peace, not_verified],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )

    asyncio.run(bot.reconcile_visitor_role(verified))
    asyncio.run(bot.reconcile_visitor_role(peace_member))

    verified.remove_roles.assert_awaited_once_with(
        not_verified,
        reason="Visitor já está verificado",
    )
    peace_member.remove_roles.assert_awaited_once_with(
        not_verified,
        reason="Peace member não é visitante nem Not Verified",
    )


def test_approved_set_assigns_peace_and_intern_without_requiring_novato(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        novato_role_id=300,
        visitor_role_id=400,
        not_verified_role_id=500,
        intern_role_id=600,
        founder_user_id=1,
    )
    bot = PeaceBot(settings)
    bot.database.initialize()
    peace = SimpleNamespace(id=200, name="Peace")
    visitor = SimpleNamespace(id=400, name="Visitor")
    not_verified = SimpleNamespace(id=500, name="Not Verified")
    intern = SimpleNamespace(id=600, name="Intern")
    guild = SimpleNamespace(
        get_role=lambda role_id: {
            200: peace,
            400: visitor,
            500: not_verified,
            600: intern,
        }.get(role_id),
        roles=[peace, visitor, not_verified, intern],
    )
    target = SimpleNamespace(
        id=10,
        name="candidate",
        nick=None,
        mention="<@10>",
        roles=[],
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
        edit=AsyncMock(),
        send=AsyncMock(),
    )
    reviewer = SimpleNamespace(
        id=20,
        guild=guild,
        mention="<@20>",
        display_name="Staff",
    )
    bot.member = AsyncMock(return_value=target)

    result = asyncio.run(
        bot.approve_set_request(
            {
                "id": 1,
                "discord_user_id": 10,
                "in_game_username": "candidate",
            },
            reviewer,
        )
    )

    assert "Set aprovado" in result
    target.add_roles.assert_awaited_once_with(
        peace,
        intern,
        reason="Set aprovado manualmente por Staff ou Management 20",
    )
    target.remove_roles.assert_any_await(visitor, reason="Set aprovado: visitante convertido em Peace")
    target.remove_roles.assert_any_await(not_verified, reason="Set aprovado: membro convertido em Peace")
