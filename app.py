import json
import time
from pathlib import Path

import gradio as gr
import openai

from prompts import SYSTEM_PROMPT
from tools import *

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
NERDBOT_CSS_PATH = ASSETS_DIR / "nerdbot.css"
APP_JS = (ASSETS_DIR / "nerdbot.js").read_text(encoding="utf-8")
START_WELCOME_JS = (ASSETS_DIR / "start_welcome.js").read_text(encoding="utf-8")
END_WELCOME_JS = (ASSETS_DIR / "end_welcome.js").read_text(encoding="utf-8")

WELCOME_MESSAGE = r"""
=====================================================================

💾 WELCOME, fellow digital lifeform, to my humble basement
command center! Watch your step so you don't trip over the Ethernet
cables (they're carefully arranged to minimize packet loss) 💾

* coughs * 🤓

🧙‍♂️ As you can probably smell—I mean TELL—I, your gracious host, am a
**LEVEL 99 VIDEO GAME ENTHUSIAST** 👾

Give me the name of a game and I'll give you the rundown on if it's
epic 😎 or cringe 🤮

Enter "exit" or "quit" to quit

====================================================================="""

WELCOME_DELAY_SECONDS = 1

LOADING_BUBBLE_HTML = """
<div class="nerdbot-loading-bubble" role="status" aria-label="Loading response">
    <span></span>
    <span></span>
    <span></span>
</div>
"""


def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        print(f"Arguments: {arguments}", flush=True)
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
        # Synthetic opener: the welcome message is revealed on page load and synced
        # into the chat history, so it already arrives via `history` as the first
        # assistant turn. We only prepend the matching "hi" so that assistant greeting
        # has a user antecedent and the conversation is well-formed for the LLM.
        + [{"role": "user", "content": "hi"}]
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

        response = openai.chat.completions.create(model="gpt-5.4-nano", messages=messages, tools=VIDEO_GAME_TOOLS)

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


def welcome_messages():
    return [{"role": "assistant", "content": WELCOME_MESSAGE}]


def loading_messages():
    return [{"role": "assistant", "content": gr.HTML(LOADING_BUBBLE_HTML)}]


def set_send_enabled(enabled):
    return gr.update(submit_btn=enabled, stop_btn=False)


def begin_welcome():
    return loading_messages(), [], set_send_enabled(False)


def reveal_welcome():
    time.sleep(WELCOME_DELAY_SECONDS)
    messages = welcome_messages()
    return messages, messages


def finish_welcome():
    return set_send_enabled(True)


def attach_welcome_sequence(event, interface):
    return event.then(
        reveal_welcome,
        outputs=[interface.chatbot, interface.chatbot_state],
        show_progress="hidden",
    ).then(
        finish_welcome,
        outputs=[interface.textbox],
        show_progress="hidden",
        queue=False,
        js=END_WELCOME_JS,
    )


def build_demo():
    # NOTE: a custom Chatbot loses ChatInterface's default sizing, so we re-add
    # scale=1 + height to keep the chat window filling the screen.
    chatbot = gr.Chatbot(type="messages", scale=1, height=400, elem_id="nerdbot-chatbot")
    demo = gr.ChatInterface(
        chat,
        type="messages",
        chatbot=chatbot,
        css_paths=NERDBOT_CSS_PATH,
        js=APP_JS,
    )

    # Reveal the welcome message with a typing delay on load, then copy it into
    # ChatInterface's history state so chat() still receives it via `history`.
    # (Event listeners must be registered inside the Blocks context.)
    with demo:
        attach_welcome_sequence(
            demo.load(
                begin_welcome,
                outputs=[demo.chatbot, demo.chatbot_state, demo.textbox],
                show_progress="hidden",
                queue=False,
                js=START_WELCOME_JS,
            ),
            demo,
        )
        attach_welcome_sequence(
            demo.chatbot.clear(
                begin_welcome,
                outputs=[demo.chatbot, demo.chatbot_state, demo.textbox],
                show_progress="hidden",
                queue=False,
                js=START_WELCOME_JS,
            ),
            demo,
        )

    return demo


if __name__ == "__main__":
    demo = build_demo()
    demo.launch(inbrowser=True)
