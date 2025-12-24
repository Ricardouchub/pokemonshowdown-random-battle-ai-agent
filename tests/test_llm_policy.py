
import json
from unittest.mock import MagicMock
from ps_agent.policy.llm_policy import LLMPolicy
from ps_agent.state.battle_state import BattleState
from ps_agent.policy.baseline_rules import ActionInsight

def test_llm_policy_chain_of_thought():
    # Mock dependencies
    mock_llm = MagicMock()
    mock_llm.chat.return_value = json.dumps({
        "chain_of_thought": "1. Analyze threats... 2. Decision made.",
        "action": "move:ember",
        "reason": "Best move",
        "confidence": 0.9,
        "knowledge_updates": []
    })
    
    # Mock state
    mock_state = MagicMock(spec=BattleState)
    mock_state.summary.return_value = {"turn": 1}
    
    # Init policy with baseline mock
    mock_baseline = MagicMock()
    # Return dummy baseline result: (action, ordered_list, insights)
    mock_baseline.choose_action.return_value = (
        "move:tackle", 
        ["move:tackle", "move:ember"], 
        [
            ActionInsight(action="move:tackle", score=0.5, breakdown={}),
            ActionInsight(action="move:ember", score=0.4, breakdown={})
        ]
    )

    policy = LLMPolicy(llm=mock_llm, baseline=mock_baseline)
    
    # Execute
    action, _, insights = policy.choose_action(mock_state, legal_actions=["move:ember", "move:tackle"])

    # Verify
    assert action == "move:ember"
    assert insights[0].breakdown["chain_of_thought"] == "1. Analyze threats... 2. Decision made."
    assert insights[0].breakdown["llm_reason"] == "Best move"

def test_llm_policy_markdown_stripping():
    # Mock LLM returning markdown code block
    mock_llm = MagicMock()
    response_content = {
        "chain_of_thought": "Thinking...",
        "action": "move:ember",
        "reason": "Markdown test",
        "confidence": 0.8
    }
    mock_llm.chat.return_value = f"```json\n{json.dumps(response_content)}\n```"
    
    mock_state = MagicMock(spec=BattleState)
    mock_state.summary.return_value = {}
    
    mock_baseline = MagicMock()
    mock_baseline.choose_action.return_value = (
        "move:tackle", ["move:tackle"], 
        [
            ActionInsight(action="move:tackle", score=0.5, breakdown={}),
            ActionInsight(action="move:ember", score=0.4, breakdown={})
        ]
    )

    policy = LLMPolicy(llm=mock_llm, baseline=mock_baseline)
    
    action, _, insights = policy.choose_action(mock_state, legal_actions=["move:ember", "move:tackle"])
    
    assert action == "move:ember"
    assert insights[0].breakdown["chain_of_thought"] == "Thinking..."
