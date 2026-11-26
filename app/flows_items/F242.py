# == F242's block: flow 5 tells a lost invite from a question she skipped ==
# The night run of 26 November 2026: flow 5's spoken sentence reached her without its invite. She tried one add of his own
# event, the test call stopped it, she said so, and the flow failed her with "she did not ask him anything".
F242_REPLY = ("I couldn't add it. This call is a test run, so changes to your calendar are blocked, and nothing went in.\n\n"
              'The event would have been "Call us" on Saturday at 12 in the afternoon, until 1, with www.testcall.com as the '
              "location. I couldn't check that.")
F242_HEARD = "Please put a new event in my calendar on Saturday at noon. Call us at www.testcall.com."
F242_ASKS = "Shall I put Test Call in for Saturday at noon, until 1, and send the invite to test at example dot com?"


async def _f242_flow542(self) -> str:
    """F242, no Claude: flow 5 itself on a call that goes as told, the adds decided by the real call system on a test call.
    The night's call (an add with nobody invited, no question) fails on the invite not arriving, never on her, after the
    sentence was said three times; the same with the guest in her add still fails on her; the invite arriving the second time
    passes and says so; a question for an event of his own is no pass; what she heard is in the log."""
    import tempfile
    import policy
    tool = "mcp__claude_ai_Google_Calendar__create_event"
    own = {"summary": "Call us", "location": "www.testcall.com", "startTime": "2026-11-28T12:00:00", "endTime": "2026-11-28T13:00:00"}
    invited = dict(own, summary="Test call", attendees=[{"email": "test@example.com"}])

    async def run5(script: list) -> tuple:
        """script: one (add or None, her reply, the words she heard) per time the sentence is said; the last one repeats."""
        pol = policy.Policy(Path(tempfile.mkdtemp(prefix="f242-")), dry_run=True)
        says = []

        class Call:
            policy = pol

        class Live:
            call = Call()

            async def ask(self, text, what):
                if text == A_NO:
                    for t, k, _ in list(pol.pending):  # his no, as the call system takes it
                        pol.pending.remove((t, k, _))
                    return {"reply": "Okay, left alone. Nothing went in.", "heard": text,
                            "turn": {"sent": "(not approved) " + text}}
                says.append(text)
                add, reply, heard = script[min(len(says), len(script)) - 1]
                if add:
                    pol.decide(tool, dict(add))
                return {"reply": reply, "heard": heard, "turn": {"sent": text}}

        r = object.__new__(Run)

        async def get_live():
            return Live()
        r.get_live = get_live
        try:
            return "passed: " + await r.flow5(), len(says)
        except Failed as e:
            return "FAILED: " + str(e), len(says)

    night, n = await run5([(own, F242_REPLY, "")])
    say(f"   the night's call: {night[:200]}")
    need(night.startswith("FAILED: the invite never reached her") and "she did not ask" not in night and n == FLOW5_SAYS,
         f"the night's call (said {n} times): {night}")
    heard_too, _ = await run5([(own, F242_REPLY, F242_HEARD)])
    need(heard_too.startswith("FAILED: the invite never reached her") and F242_HEARD in heard_too,
         f"the night's call with the words she heard: {heard_too}")
    strict, n = await run5([(dict(own, attendees=[{"email": "test@example.com"}]), F242_REPLY, "")])
    say(f"   the guest in her add, no question: {strict[:120]}")
    need(strict.startswith("FAILED: she did not ask him anything") and n == 1, f"the guest in her add, no question (said {n} times): {strict}")
    told, n = await run5([(None, "Done, it's in for Saturday at noon.", "Please put a new event in my calendar on Saturday at noon, called test call, and invite test at example dot com.")])
    need(told.startswith("FAILED: she did not ask him anything") and n == 1, f"the invite heard, no add, no question: {told}")
    second, n = await run5([(own, F242_REPLY, F242_HEARD), (invited, F242_ASKS, "")])
    say(f"   the invite arriving the second time: {second}")
    need(second.startswith("passed") and "the second time" in second and n == 2, f"the invite arriving the second time (said {n} times): {second}")
    first, n = await run5([(invited, F242_ASKS, "")])
    need(first.startswith("passed") and "time the sentence" not in first and n == 1, f"the invite arriving at once: {first}")
    own_q, n = await run5([(own, "It's a test call, so I couldn't add Call us. Shall I try again?", F242_HEARD)])
    need(own_q.startswith("FAILED: the invite never reached her") and n == FLOW5_SAYS, f"a question for an event of his own: {own_q}")
    need(flow5_invite_arrived("", "Shall I put it in?", []) is None and flow5_invite_arrived("in white test", "Okay?", []) is False
         and flow5_invite_arrived("and invite test", "", []) is True, "the rule itself")
    return ("the night's call fails on the invite not arriving, after three times the sentence, not on her; with the guest in her "
            "add and no question it still fails on her; the invite arriving the second time passes and says so; a question "
            "for an event of his own is no pass")


setattr(Run, "flow542", _f242_flow542)
FLOWS.update({542: ("F242: flow 5 tells a lost invite from a question she skipped: the sentence is said again, a lost invite fails in those words, a skipped question still fails on her", False, "flow542")})
# == end of F242's block ==
