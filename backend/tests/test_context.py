from app.context import ConversationContext, Turn


def test_context_bounds_to_max_turns():
    ctx = ConversationContext(max_turns=3)
    for i in range(5):
        ctx.add(Turn(speaker="customer", text=f"turn {i}", ts=float(i)))
    assert len(ctx) == 3


def test_as_prompt_text_excludes_latest_turn():
    ctx = ConversationContext(max_turns=5)
    ctx.add(Turn(speaker="customer", text="first", ts=0.0))
    ctx.add(Turn(speaker="agent", text="second", ts=1.0))
    ctx.add(Turn(speaker="customer", text="third (latest)", ts=2.0))
    text = ctx.as_prompt_text()
    assert "first" in text
    assert "second" in text
    assert "third (latest)" not in text


def test_as_prompt_text_empty_context():
    ctx = ConversationContext(max_turns=5)
    assert ctx.as_prompt_text() == ""
