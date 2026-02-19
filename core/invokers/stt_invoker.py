from langchain_core.runnables import RunnableLambda
from core.models.stt import transcribe_audio

def invoke_stt(data):
    data['user_text'] = transcribe_audio(data['user_audio'])
    return data

stt_invoker = RunnableLambda(invoke_stt)
