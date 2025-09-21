import json
from unittest.mock import Mock, patch

from app.ai_assistant import AIAssistantService


def test_process_chat_executes_tool_and_returns_final_response(monkeypatch):
    """Simulate Responses API function_call flow and ensure tool executed and final response returned."""
    service = AIAssistantService('test-key', 'gpt-5')

    # First call: Responses API returns an output with a function_call (stringified arguments)
    func_call = {
        'type': 'function_call',
        'name': 'get_calendar_events',
        'arguments': json.dumps({'date': '2025-09-22', 'start_date': '', 'end_date': ''})
    }
    first_response = {'output': [func_call]}

    # Second call (after tool execution): final response
    final_output = {'output_text': 'Hai 2 eventi domani: Riunione 10:00, Standup 15:00'}

    # Mock _create_chat_completion to return first_response then final_output
    call_seq = [first_response, final_output]

    def fake_create(self, **kwargs):
        return call_seq.pop(0)

    monkeypatch.setattr(AIAssistantService, '_create_chat_completion', fake_create)

    # Mock _execute_tool_call to return a predictable result
    def fake_execute(self, tool_name, arguments, user):
        assert tool_name == 'get_calendar_events'
        assert arguments.get('date') == '2025-09-22'
        return {'success': True, 'events': [{'title': 'Riunione', 'start': '2025-09-22T10:00:00'}]}

    monkeypatch.setattr(AIAssistantService, '_execute_tool_call', fake_execute)

    # Run process_chat with a fake user
    fake_user = Mock()
    fake_user.ai_language = 'italian'
    fake_user.id = 1

    result = service.process_chat('che cosa ho da fare domani?', fake_user)

    assert isinstance(result, str)
    assert 'Hai 2 eventi' in result or 'Riunione' in result
