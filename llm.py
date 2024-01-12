import json
import os

import openai
import google.generativeai as google_genai
import streamlit as st

from summarizer.sbert import SBertSummarizer

SUPPORTED_MODELS = ['gemini-pro', 'gpt-3.5-turbo', 'gpt-4']
openai.api_key = os.environ.get('OPENAI_API_KEY')
google_genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))

def call_openai(prompt, temperature=0.8, model_name='gpt-4'):
    model_msg = [
        {
            'role': 'user',
            'content': prompt
        }
    ]

    response = openai.ChatCompletion.create(
        model=model_name,
        messages=model_msg,
        temperature=temperature,
    )

    ret = response.choices[0].message['content'].strip()
    return ret

def call_google(prompt, temperature=0.8, model_name='gemini-pro'):
    model = google_genai.GenerativeModel('gemini-pro',
        generation_config=google_genai.types.GenerationConfig(
        temperature=temperature)
    )

    ret = model.generate_content(prompt).text
    return ret

def call_llm(prompt, model_name, **kwargs):
    if 'gpt' in model_name:
        try:
            return call_openai(prompt, model_name=model_name, **kwargs)
        except Exception as e:
            # Handle the exception, log it, or pass it up
            print(f"Model {model_name} doesn't work with OpenAI's ChatCompletion API: {e}")
            # Optionally, re-raise the exception
            raise
    elif 'gemini' in model_name:
        try:
            return call_google(prompt, model_name=model_name, **kwargs)
        except Exception as e:
            print(f"Model {model_name} doesn't work with Google's GenAI API: {e}")
            raise
    else:
        print(f"Model {model_name} not supported.")
        raise Exception

def extract_json_from_response(response):
    try:
        # Find the start and end of the JSON object/array
        start = response.find('[')
        end = response.rfind(']') + 1  # +1 to include the closing brace
        if start != -1 and end != -1:
            json_str = response[start:end]
            return json.loads(json_str)
        else:
            raise ValueError("JSON structure not found in response.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")

def generate_personas(topic, num_personas, cfg):

    # Otherwise generate it.
    prompt = cfg['prompts']['persona_creation']
    prompt = prompt.replace("[TOPIC]", topic)
    prompt = prompt.replace("[NUM_PERSONAS]", str(num_personas))


    response = call_llm(
                prompt,
                cfg['llm_params']['model_name'],
                temperature=cfg['llm_params']['temperature']
                )

    print(f"DEBUG LLM RESPONSE: {response}")
    return extract_json_from_response(response)

model = SBertSummarizer('paraphrase-MiniLM-L6-v2')
def check_shorten(debate_history, shorten_after):
    num_words = len(str(debate_history).split())
    if num_words > shorten_after:
        print("SHORTENING...")
        ratio = (shorten_after - 100) / num_words
        new_debate_history = []
        for line in debate_history:
            line = line.copy()
            new_debate_history.append(model(line['argument'], ratio))
    else:
        print("NOT SHORTENING...", num_words)
        new_debate_history = debate_history
    return new_debate_history

def simulate_debate(topic, personas, cfg):
    rounds = cfg['debate_params']['num_debate_rounds']
    cont_mode = cfg['debate_params']['enable_continuous_mode']
    debate_history = []
    for i in range(int(rounds)):
        for p_idx, persona in enumerate(personas):


            if cont_mode:
                prompt = cfg['prompts']['debate_start'] if len(debate_history) == 0 else cfg['prompts']['debate']
                str_debate = str(check_shorten(debate_history, cfg['debate_params']['transcript_word_limit']))
                prompt = prompt.replace("[HISTORY]", str_debate)
            else:
                if i == 0:
                    prompt = cfg['prompts']['debate_start']
                else:
                    prompt = cfg['prompts']['debate']
                    str_debate = str(shortened_prev_round_debate_history)
                    prompt = prompt.replace("[HISTORY]", str_debate)

            prompt = prompt.replace("[TOPIC]", topic).replace("[NAME]", persona['name']).replace("[DESC]", persona['description'])

            if cfg['debate_params']['limit_response_length']:
                limiter = cfg['prompts']['response_length'].replace('[RESPONSE_LENGTH]',
                                                                    cfg['debate_params']['response_length'])
                prompt = prompt.replace("[LIMITER]", limiter)
            else:
                prompt = prompt.replace("[LIMITER]", "")

            response = call_llm(prompt, cfg['llm_params']['model_name'], temperature=cfg['llm_params']['temperature'])

            # Streamlit chat message
            display_name = persona['name'] if cfg['ux_params']['show_persona_desc'] else f"Persona {p_idx}"
            with st.chat_message(str(p_idx)):
                st.write(f"{display_name}:\n", response)

            debate_history.append({"persona": display_name, "argument": response})
        if not cont_mode:
            prev_round_debate_history = debate_history.copy()
            shortened_prev_round_debate_history = check_shorten(prev_round_debate_history, cfg['debate_params']['transcript_word_limit'])
