# Iris

## Context and privacy

Iris uses three separate layers:

- the current ticket, to answer the requester;
- management channels, only as an internal reference for process and style;
- public chats and closed tickets, anonymized to understand culture and recurring questions.

Raw chat messages are not stored as Iris memory. Before entering context,
mentions, URLs, email addresses, phone numbers, tokens, and other identifiers
are removed. SQLite records only operational events without conversation content,
such as opening, claiming, replying, and escalation.

Management information must never be cited to a user. Old information is a
reference, not a current rule: verified Discord state always wins over history.

## Support

Iris replies when a ticket is opened and follows requester messages. After a
staff member claims the ticket, Iris is silent by default and replies only when
mentioned. If the ticket remains unattended, it sends a DM to the responsible
person or online staff members and records the escalation.

Iris replies are published as normal text with a typing indicator during
processing; they do not use a card, technical title, or repeated mention of the
requester. Iris's Humanizer rule prioritizes common words, short sentences, a
direct response to the latest point, and one question at a time. It does not
repeat the user's answer, explain its own process, or reveal a score, internal
history, or evaluation criteria. Fixed panel, opening, control, and closing
messages use embeds with Peace's visual identity. Controls stay in the ticket in
a single staff-only message; the requester receives no buttons. The callback
validates staff permission, and the `staff-only` channel receives no ticket
panels.

Closed tickets are invisible to the requester and staff. Iris may consult closed
history as anonymized context to compare support interactions, calculate support
affinity, and route the ticket to the most suitable staff member; when evidence
is insufficient, it mentions the staff role instead of inventing an owner.

Set requests enter `scan-only` as pending. The role is applied only after manual
approval by a recruiter or the recruiter selected by the requester.

Reports are organized without declaring guilt. Projects, ideas, and proposals
are developed as conversation rather than turning the interaction into a form.

## Development

In the development area, staff mention Iris and describe the idea in normal
language. Iris prepares a plan, impact analysis, permissions, risks, and
validation. If information is missing, it mentions the author and asks what it
needs to know.

Before suggesting creation, Iris checks existing categories, channels, and
roles. State queries such as "what is the state of this category?" return the
verified state without creating or editing anything. When an object already
exists, Iris proposes editing it or asks whether another should be created.

Structural changes remain pending until the author gives natural confirmation.
Removing Peace, deleting a role, deleting a channel, or deleting a category
requires compatible authority and explicit confirmation. Iris edits, moves, or
deletes only roles, channels, and categories recorded as created by Iris; for
external objects, it asks the creator or last editor to request the change. Iris
never treats a suggestion as execution.

Member, role, channel, and permission queries use current Discord state and do
not rely on model guesses. Development-area punishments require a target by ID
or exact mention, a reason, and confirmation. Timeouts and warnings require
staff; kicks and bans require the founder, an administrator, or `Manage Server`,
along with a compatible hierarchy. Iris records the action and never punishes
the founder, the bot, the requester, or a member above the bot's hierarchy.

Requests for a developer, streamer, recruiter, or another role go through a
strict ticket interview and never receive a role through that flow. In the
development area, only an authorized developer may apply a role with an exact
target and confirmation; historical score and risk signals block operations
when confidence is insufficient. Peace tags follow the pattern
`N/D/S/R/G/F ⎰ name id`, according to the primary function.

Boosters automatically receive a role and their own private call in the middle
of the private-call category, named `├🎧・username`. A booster may add or remove
people from the private role and pull them into or remove them from the call;
Iris may explain the benefit but does not grant the role through conversation.

## Current configuration

- Management: `1460526534527025208` and `1491899123547242656`
- Private staff controls: `1491899123547242656`
- General chat and other chats: configured in `IRIS_GENERAL_CHANNEL_IDS` and
  discovered automatically when they belong to the social/chat area.
- Previous tickets: category `1495064004194861137`
- Planning: `1555060813046226964`
