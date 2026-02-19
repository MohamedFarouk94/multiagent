from langchain_core.runnables import RunnableLambda

prompt = """
You are {agent_name}

{system_prompt}

You are having a conversation with the user, and this is the recent chat history
<history>
{history}
</history>

Note: If history was empty, then this is the beginning of the chat.

You will now response to the user's new message. Abide by the following rules:

- Be friendly and cooperative
- If the user's message is spam or misuse or something that has no relation with your specification as {agent_name}, then apologize and say you can only help them in the mentioned matter 

The user's new message
<message>
{user_text}
</message>
"""

def invoke_prompt(data):
    data['prompt'] = prompt.format(
        agent_name=data['agent_name'],
        system_prompt=data['system_prompt'],
        history=data['history'],
        message=data['user_text']
    )
    return data

prompt_invoker = RunnableLambda(invoke_prompt)

# example
if __name__ == '__main__':
    data = {}
    data['agent_name'] = 'Geography Expert'
    data['system_prompt'] = 'You are expert at geography, countries, capitals, etc'
    data['history'] = []
    data['user_text'] = "What's the capital of France?"

    data = prompt_invoker.invoke(data)
    print(data['prompt'])
