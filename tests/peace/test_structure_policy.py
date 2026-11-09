from pathlib import Path

from bot.operations.maintenance import CATEGORY_NAMES, ROLE_COLOURS, VERIFICATION_CHANNEL_NAME


def test_verification_and_structural_names_are_english():
    assert VERIFICATION_CHANNEL_NAME == "verify"
    assert CATEGORY_NAMES == {
        "reception": "[🎫] RECEPTION",
        "staff": "[🛡️] STAFF",
        "development": "[💻] DEVELOPERS",
        "records": "[ℹ️] RECORDS",
        "social": "[🔔] SOCIAL LOUNGE",
        "support": "[☎️] SUPPORT",
        "calls": "[🎙️] CALLS",
        "private_calls": "[🎙️] PRIVATE CALLS",
        "verification": "[🔐] VERIFICATION",
        "closed_tickets": "[🎟️] CLOSED TICKETS",
    }


def test_role_palette_covers_every_migrated_public_role():
    assert {
        "Peace",
        "Staff",
        "Management",
        "Manager ⎰ Deputy Delegate",
        "Visitor",
        "Elite ⎰ Special Agent",
        "Rookie ⎰ Agent",
        "Member ⎰ Recruit",
        "Dev",
        "Intern",
        "AIs",
        "Not Verified",
        "General Director",
        "Superintendent",
    } <= ROLE_COLOURS.keys()
    assert all(0 < colour < 0x1000000 for colour in ROLE_COLOURS.values())


def test_records_channels_are_not_public_onboarding_surfaces():
    # The maintenance policy must configure media, clips, and dashboard through
    # role allowlists so Not Verified cannot inherit access from @everyone.
    source = Path("bot/operations/maintenance.py").read_text(encoding="utf-8")
    assert 'configure_text(channel, guild, allowed=registration_roles, send=send)' in source
    assert 'configure_text(channel, guild, allowed=[], public=True, send=send)' not in source


def test_visitor_surface_is_explicit_and_spam_control_is_private():
    source = Path("bot/operations/maintenance.py").read_text(encoding="utf-8")
    assert 'allowed=[peace, visitor, staff, manager, founder]' in source
    assert 'await configure_text(automod, guild, allowed=[], send=False)' in source
    assert 'await set_default_access(afk, guild, view=True, connect=False, speak=False)' not in source

    main_source = Path("bot/main.py").read_text(encoding="utf-8")
    assert "set_permissions" not in main_source
    assert "PermissionOverwrite" not in main_source
    assert "overwrites=" not in main_source
