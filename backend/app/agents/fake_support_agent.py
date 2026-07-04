FAKE_AGENT_REPLY = "Thanks for your message. A support agent will help you shortly."


class FakeSupportAgent:
    async def reply(self, user_message: str, history=None, **kwargs) -> str:
        return FAKE_AGENT_REPLY

    async def reply_stream(self, user_message: str, history=None, **kwargs):
        yield {"type": "token", "content": FAKE_AGENT_REPLY}
