import os
from .invokers.prompt_invoker import prompt_invoker
from .invokers.tts_invoker import tts_invoker
from .invokers.stt_invoker import stt_invoker
from .invokers.llm_invoker import llm_invoker

text_chain = prompt_invoker | llm_invoker
audio_chain = stt_invoker | text_chain | tts_invoker

if __name__ == '__main__':
    data = {}
    data['agent_name'] = 'Geography Expert'
    data['system_prompt'] = 'You are expert at geography, countries, capitals, etc'
    data['history'] = []
    
    text_data = data.copy()

    audio_data = data.copy()
    audio_data['user_audio'] = "samples/input.wav"

    command = input("To test text chain, enter 1.\nTo text audio chain enter any thing else.\n")

    if command == '1':
        text_data['user_text'] = input("\nEnter your query: ")
        text_data = text_chain.invoke(text_data)
        print(text_data['agent_text'])

    else:
        print('\nSpeak now!!')
        os.system('arecord samples/input.wav')
        audio_data = audio_chain.invoke(audio_data)
        os.system('ffplay -nodisp -autoexit samples/output.mp3')
