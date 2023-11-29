# Welcome to a hacked version of Chainlit 👋

## Important note

This repository is a fork of the 0.7.1 of Chainlit which has been adapted to create a bot with a specialized Chainlit UI for this project:

https://github.com/onepointconsulting/data-questionnaire-agent

This is not for general purpose use.

For the real thing please go to https://chainlit.io

**Build Python LLM apps in minutes ⚡️**

Chainlit lets you create ChatGPT-like UIs on top of any Python code in minutes! Some of the key features include intermediary steps visualisation, element management & display (images, text, carousel, etc.) as well as cloud deployment.

[![](https://dcbadge.vercel.app/api/server/ZThrUxbAYw?style=flat)](https://discord.gg/k73SQ3FyUh)
[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/chainlit_io.svg?style=social&label=Follow%20%40chainlit_io)](https://twitter.com/chainlit_io)
[![CI](https://github.com/Chainlit/chainlit/actions/workflows/ci.yaml/badge.svg)](https://github.com/Chainlit/chainlit/actions/workflows/ci.yaml)

https://github.com/Chainlit/chainlit/assets/13104895/e347e52c-35b2-4c35-8a88-f8ac02dd198e

## Installation

Open a terminal and run:

```bash
$ pip install chainlit
$ chainlit hello
```

If this opens the `hello app` in your browser, you're all set!

## 📖 Documentation

Please see [here](https://docs.chainlit.io) for full documentation on:

- Getting started (installation, simple examples)
- Examples
- Reference (full API docs)

## 🚀 Quickstart

### 🐍 Pure Python

Create a new file `demo.py` with the following code:

```python
import chainlit as cl


@cl.on_message  # this function will be called every time a user inputs a message in the UI
async def main(message: str):
    # this is an intermediate step
    await cl.Message(author="Tool 1", content=f"Response from tool1", indent=1).send()

    # send back the final answer
    await cl.Message(content=f"This is the final answer").send()
```

Now run it!

```
$ chainlit run demo.py -w
```

<img src="/images/quick-start.png" alt="Quick Start"></img>

### 🔗 With LangChain

Check out our plug-and-play [integration](https://docs.chainlit.io/integrations/langchain) with LangChain!

### 📚 More Examples - Cookbook

You can find various examples of Chainlit apps [here](https://github.com/Chainlit/cookbook) that leverage tools and services such as OpenAI, Anthropiс, LangChain, LlamaIndex, ChromaDB, Pinecone and more.

## 🛣 Roadmap

- [ ] New UI elements (spreadsheet, video, carousel...)
- [ ] Create your own UI elements via component framework
- [ ] DAG-based chain-of-thought interface
- [ ] Support more LLMs in the prompt playground
- [ ] App deployment

Tell us what you would like to see added in Chainlit using the Github issues or on [Discord](https://discord.gg/ZThrUxbAYw).

## 💁 Contributing

As an open-source initiative in a rapidly evolving domain, we welcome contributions, be it through the addition of new features or the improvement of documentation.

For detailed information on how to contribute, see [here](.github/CONTRIBUTING.md).

## License

Chainlit is open-source and licensed under the [Apache 2.0](LICENSE) license.
