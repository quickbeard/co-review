import pytest

from pr_agent.algo.learning_extractor import extract_learning_candidate


@pytest.mark.parametrize(
    "comment_body",
    [
        "",
        "   ",
        "/review",
        "short preference",
        "This sentence is long enough but has no project preference marker.",
    ],
)
def test_extract_learning_candidate_returns_none_for_non_candidates(comment_body):
    assert extract_learning_candidate(comment_body, app_name="pr-agent") is None


def test_extract_learning_candidate_removes_agent_mention():
    text = "@pr-agent, We prefer explicit typing in this project and avoid implicit casts."

    extracted = extract_learning_candidate(text, app_name="pr-agent")

    assert extracted == "We prefer explicit typing in this project and avoid implicit casts."


def test_extract_learning_candidate_matches_marker_case_insensitively():
    text = "@PR-Agent: PLEASE AVOID introducing wildcard imports in this repo."

    extracted = extract_learning_candidate(text, app_name="pr-agent")

    assert extracted == "PLEASE AVOID introducing wildcard imports in this repo."
