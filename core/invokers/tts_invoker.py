from langchain_core.runnables import RunnableLambda
from core.models.tts import synthesize_speech

def invoke_tts(data):
    data['agent_audio'] = synthesize_speech(data['agent_text'])
    return data

tts_invoker = RunnableLambda(invoke_tts)
