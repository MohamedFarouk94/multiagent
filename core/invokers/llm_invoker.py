from langchain_core.runnables import RunnableLambda
from models.llm import ask_llm

def invoke_llm(data):
    data['agent_text'] = ask_llm(data['prompt'])
    return data

llm_invoker = RunnableLambda(invoke_llm)
