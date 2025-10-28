# 🎮 Video Game Nerd Bot

A highly enthusiastic AI agent with deep gaming knowledge, ready to geek out about your favorite video games!

## 🚀 Try it Live

**[Launch the Bot on Hugging Face Spaces](https://huggingface.co/spaces/mike-ai-guy/vg-nerd-bot)**

## 🤖 What is This?

This is an AI-powered gaming assistant that embodies the personality of a passionate video game nerd. Ask it anything about games, request recommendations, or dive into gaming trivia—it responds with enthusiasm, references, Easter eggs, and plenty of *asterisk actions*.

## ⚙️ How It Works

- **AI Model**: Powered by GPT-4.1-nano via the OpenAI API
- **Game Database**: Real-time game data from the [RAWG Video Games Database](https://rawg.io/apidocs)
- **Tech Stack**: Built with vanilla Python and minimal dependencies:
  - `openai` - For the AI agent
  - `gradio` - For the chat interface
  - `requests` - For RAWG API calls
- **Tools**: The agent can search games, fetch details, filter by platforms/genres, and more

The bot uses function calling to dynamically query game information and delivers responses in true gaming nerd fashion.

## 🛠️ Local Setup
*NOTE: I set this up using `uv`, check out the [official documentation](https://docs.astral.sh/uv/getting-started/installation/) for a guide on installation (it's super easy!)*

1. Clone the repository
2. Install dependencies:
```
uv sync
```

*If that fails then run `uv pip sync requirements.txt`*

3. Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key
RAWG_API_KEY=your_rawg_keyse
```

4. Run the app:
```
uv run app.py
```

## 📝 License

Feel free to use and modify!
