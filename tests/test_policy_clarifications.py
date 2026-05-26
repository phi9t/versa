from versa.policy import clarification_for_slot


def test_clarification_for_scope_is_conversational():
    message = clarification_for_slot("scope")
    assert message != "I need one missing detail before solving: scope"
    assert "building" in message.lower()
