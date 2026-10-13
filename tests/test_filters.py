from kytsubot import Command, F, Keyword, Message, SenderType


def message(text: str | None) -> Message:
    return Message(
        message_id="msg_1",
        chat_id="cht_1",
        sender_type=SenderType.USER,
        text=text,
    )


def test_command_extracts_arguments() -> None:
    result = Command("start")(message("/start campaign"))
    assert isinstance(result, dict)
    assert result["command"].command == "start"
    assert result["command"].args == "campaign"


def test_keyword_and_magic_filter() -> None:
    event = message("Salom")
    assert Keyword("salom")(event)
    assert (F.text.casefold() == "salom")(event)
    assert F.text.startswith("Sal")(event)
    assert not F.text.endswith("x")(event)

