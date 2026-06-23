# lib/discord — costanti dell'adapter: intents + permessi di invito.

import discord


# the gateway intents tokeniko's bot needs. message_content is a PRIVILEGED intent — it must also be
# toggled ON in the Developer Portal (Bot -> Privileged Gateway Intents), otherwise inbound `content`
# arrives empty. guild + DM message events are already part of Intents.default().
def default_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    return intents


# OAuth2 invite permission bits for adding the bot to a server (scope "bot"):
#   VIEW_CHANNEL (1<<10) | SEND_MESSAGES (1<<11) | READ_MESSAGE_HISTORY (1<<16)
# = 68608. The minimal set to read channels + post + read history.
INVITE_PERMISSIONS = (1 << 10) | (1 << 11) | (1 << 16)
