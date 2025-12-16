from ps_agent.inference.set_inference import init_belief
from ps_agent.knowledge.randbats_sets import SetHypothesis


def test_belief_updates_filter_candidates():
    priors = {
        "testmon": [
            SetHypothesis(
                moves=("move-a", "move-b"),
                item="leftovers",
                ability="levitate",
                prior_prob=0.5,
                posterior_prob=0.5,
            ),
            SetHypothesis(
                moves=("move-c", "move-d"),
                item="choicescarf",
                ability="intimidate",
                prior_prob=0.5,
                posterior_prob=0.5,
            ),
        ]
    }
    belief = init_belief("testmon", priors=priors)
    updated = belief.update_with_move("move-a")
    assert len(updated.candidates) == 1
    assert updated.candidates[0].item == "leftovers"
