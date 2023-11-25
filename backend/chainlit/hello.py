# This is a simple example of a chainlit app.

from chainlit import AskUserMessage, Message, on_chat_start
from chainlit.server import build_dir


@on_chat_start
async def main():

    await Message(content="""
The project consists of the following services:

Frontend: A React application that provides the user interface for interacting with the chatbot.

Service2: A Python (FastAPI)-based backend that coordinates the communication between the frontend and Service3. This service also manages the interaction history between the user and the chatbot.

Service3: Another Python (FastAPI)-based backend hosting the chatbot algorithm. This service communicates with the AI engine (OpenAI GPT-3.5-turbo) to process user queries and generate suitable responses.

Redis: A Redis server used for state storage across the services.

Postgres: A Postgres server acting as a database for storing vector embeddings.


To get the project up and running, make sure Docker is installed on your system.

Then, run the following command:

docker-compose up
This command starts all services using the docker-compose.yml file. It downloads the necessary Docker images, creates associated containers, and gets them running together.

Data Population
The provided insert_data.py script can be used to populate the Postgres database with your data. To do this, run the script once the services are up and running. It will connect to the Postgres service, create the necessary tables, and insert data into them.

<strong>Test</strong>

""").send()

    res = await AskUserMessage(content=build_dir + ":: What is your name?", timeout=30).send()

    if res:
        await Message(
            content=f"Your name is: {res['content']}.\nChainlit installation is working!\nYou can now start building your own chainlit apps!",
        ).send()
