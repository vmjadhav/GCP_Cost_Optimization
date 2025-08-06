from .bigquery_cost_optimizer_prompt import description, instruction
import asyncio
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.sessions import Session
from google.genai import types
from google.adk.tools import google_search  # The Google Search tool
from bigquery.slot_utilization_gemini import get_bigquery_slot_utilization_for_project
from bigquery.bigquery_byte_scanned import get_query_demand
from bigquery.optimize_bigquery_slots import optimize_slots
import os
from dotenv import load_dotenv
import sys
import textwrap
import json
sys.path.append(".")
import google.cloud.logging

# 1. Load environment variables from the agent directory's .env file
load_dotenv()
model_name = os.getenv("MODEL")

cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()


# Create an async main function
async def bigquery_cost_optimizer_agent(prompt):
    """
        Use Google ADK LlmAgent with google_search tool to optimize bigquery cost.
    """
    
    # 2. Set or load other variables
    app_name = 'big_query_optimizer_agent'
    user_id_1 = 'user001'
    session = 'fsession001'


    # 3. Define Your Agent
    root_agent = Agent(
        model=model_name,
        name="BigQueryOptimizerAgent",
        description= description,
        instruction= instruction,
        tools=[get_query_demand, get_bigquery_slot_utilization_for_project, optimize_slots]
    )

    # 3. Create a Runner
    runner = InMemoryRunner(
        agent=root_agent,
        app_name=app_name,
    )

    # 4. Create a session
    my_session = await runner.session_service.create_session(
        app_name=app_name, user_id=user_id_1, session_id = session
    )

    # 5. Prepare a function to package a user's message as
    # genai.types.Content, run it asynchronously, and iterate
    # through the response 
    async def run_prompt(session: Session, new_message: str):
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$')
        print('#### New prompt :: ', new_message)
        print('------------------------------------------------------------- ')
        content = types.Content(
                role='user', parts=[types.Part.from_text(text=new_message)]
            )
        print('####  User says: ', content.model_dump(exclude_none=True))
        print('------------------------------------------------------------- ')
        async for event in runner.run_async(
            user_id=user_id_1,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'#### {event.author}: {event.content.parts[0].text}')
                return event.content.parts[0].text
        cloud_logging_client.close()


    # 6. Use this function on a new query
    result = await run_prompt(my_session, prompt)
    # Specify the filename
    filename = "bigquery_slot_optimization_result.txt"
    #result = json.dumps(result, indent=4)
    # Write to a JSON file
    #with open(filename, "w") as json_file:
    #    json.dump(result, json_file, indent=4)  # indent=4 for pretty formatting


    # # Wrap the text so each line is at most 50 characters long
    # wrapped_text = textwrap.fill(result, width=100)
    # # Write the wrapped text to a file
    # with open(filename, 'w') as file:
    #     file.write(wrapped_text)

    # print(f"Content saved to {filename}")
    return result

asyncio.run(bigquery_cost_optimizer_agent("How to optimize slot usage for bigquery?"))