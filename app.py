import json

import gradio as gr
import openai

from prompts import SYSTEM_PROMPT
from tools import *

def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        tool = globals().get(tool_name)
        result = tool(**arguments) if tool else {}
        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
    return results

def chat(message, history):
    """Conduct a chat exchange with the model, forwarding prior history and the newest user prompt."""
    persona_reminder = (
        "REMINDER: Maintain your persona. Let your gaming knowledge gush out with references, Easter eggs, deep-cut trivia, and self-aware nerd humor. Use ample asterisk actions."
    )
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [
            {
                "role": "user",
                "content": f"{message}\n\n{persona_reminder}",
            }
        ]
    )
    done = False
    while not done:

        # This is the call to the LLM - see that we pass in the tools json

        response = openai.chat.completions.create(model="gpt-4.1-nano", messages=messages, tools=VIDEO_GAME_TOOLS)

        finish_reason = response.choices[0].finish_reason
        
        # If the LLM wants to call a tool, we do that!
         
        if finish_reason=="tool_calls":
            message = response.choices[0].message
            tool_calls = message.tool_calls
            results = handle_tool_calls(tool_calls)
            messages.append(message)
            messages.extend(results)
        else:
            done = True

    return response.choices[0].message.content


if __name__ == "__main__":
    gr.ChatInterface(chat, type="messages").launch()