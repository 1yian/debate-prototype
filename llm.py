import json
import os

import openai
import google.generativeai as google_genai
import streamlit as st

from collections import namedtuple
import uuid
# from rag import cohere_rag_pipeline

SUPPORTED_MODELS = ['gemini-pro', 'gpt-3.5-turbo', 'gpt-4']
openai.api_key = os.environ.get('OPENAI_API_KEY')
google_genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))


class Agent:
    def __init__(self, title, desc, emoji=''):
        self.title = title
        self.desc = desc
        self.emoji = emoji
        self.color = None
        self._recently_expanded = False

    def __str__(self):
        return f"""{{"title": {{{self.title}}}, "description": {{{self.desc}}}, "emoji": {{{self.emoji}}}}}"""


def call_openai(prompt, temperature=0.8, model_name='gpt-4'):
    print(prompt)
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
    persona_dict = extract_json_from_response(response)
    ret = []
    for persona in persona_dict:
        ret.append(Agent(persona['title'], persona['description'], persona['emoji']))

    return ret


def add_persona(topic, current_personas, cfg):
    prompt = cfg['prompts']['persona_addition']
    prompt = prompt.replace("[TOPIC]", topic)
    prompt = prompt.replace("[CURRENT_PERSONAS]", "{" + ", ".join(map(str, current_personas)) + "}")
    response = call_llm(
        prompt,
        cfg['llm_params']['model_name'],
        temperature=cfg['llm_params']['temperature']
    )

    response = "[" + response + "]"
    print(response)
    persona = extract_json_from_response(response)[0]
    return Agent(persona['title'], persona['description'], persona['emoji'])


def check_shorten(debate_history, shorten_after):
    from summarizer.sbert import SBertSummarizer
    model = SBertSummarizer('paraphrase-MiniLM-L6-v2')
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


def debate_round(topic, agents, cfg, last_round_debate_history=[], current_debate_history=[]):
    debate_history = current_debate_history
    shortened_prev_round_debate_history = ""
    cont_mode = cfg['debate_params']['enable_continuous_mode']
    if not cont_mode and len(last_round_debate_history) > 0:
        prev_round_debate_history = last_round_debate_history.copy()
        shortened_prev_round_debate_history = check_shorten(prev_round_debate_history,
                                                            cfg['debate_params']['transcript_word_limit'])
    for i, agent in enumerate(agents):
        if cont_mode:
            prompt = cfg['prompts']['debate_start'] if len(debate_history) == 0 else cfg['prompts']['debate']
            str_debate = str(check_shorten(debate_history, cfg['debate_params']['transcript_word_limit']))
            prompt = prompt.replace("[HISTORY]", str_debate)
        else:
            if len(last_round_debate_history) == 0:
                prompt = cfg['prompts']['debate_start']
            else:
                prompt = cfg['prompts']['debate']
                str_debate = str(shortened_prev_round_debate_history)
                prompt = prompt.replace("[HISTORY]", str_debate)
        prompt = prompt.replace("[TOPIC]", topic).replace("[NAME]", agent.title).replace("[DESC]", agent.desc)

        if cfg['debate_params']['limit_response_length']:
            limiter = cfg['prompts']['response_length'].replace('[RESPONSE_LENGTH]',
                                                                cfg['debate_params']['response_length'])
            prompt = prompt.replace("[LIMITER]", limiter)
        else:
            prompt = prompt.replace("[LIMITER]", "")

        print(f"We are now on agent {i} {agent.title}")
        found = False
        for instance in current_debate_history:
            print(f"Looking for {agent.title}, looking at {instance['persona']}")
            if instance['persona'].lower() == agent.title.lower():
                found = True
                response = instance['argument']
                break

        if found:
            print(f"I have found a match for {agent.title}")
        else:
            print(f"I have not found a match for {agent.title}")
        if not found:
            response = call_llm(prompt, cfg['llm_params']['model_name'], temperature=cfg['llm_params']['temperature'])
            # Streamlit chat message
            display_name = agent.title
            display_icon = agent.emoji if len(agent.emoji) > 0 else agent.title
            instance = {"icon": display_icon, "persona": display_name, "argument": response, "color": agent.color, 'usr_rating': 0}
            if agent.title not in [instance['persona'] for instance in current_debate_history]:
                debate_history.append(instance)
                print(f"Adding a response from {display_name}")
                write_message(instance)
    return debate_history


def write_message(instance_dict):
    icon, name, response, color, usr_rating = instance_dict['icon'], instance_dict['persona'], instance_dict['argument'], instance_dict['color'], instance_dict['usr_rating']
    def add_to_summary_positive():
        summary_instance_dict = {'icon': icon, 'persona': name, 'argument': response, 'color': color}
        # Add or update the instance in summary_history_pos
        if instance_dict not in st.session_state.summary_history_pos:
            st.session_state.summary_history_pos.append(summary_instance_dict)

        # Set usr_rating to 1 or toggle to 0 if already 1
        print(instance_dict.get('usr_rating'))
        if instance_dict.get('usr_rating') != 1:
            instance_dict['usr_rating'] = 1
        else:
            instance_dict['usr_rating'] = 0
            # Remove from summary_history_pos if present
            while summary_instance_dict in st.session_state.summary_history_pos:
                st.session_state.summary_history_pos.remove(summary_instance_dict)

        while summary_instance_dict in st.session_state.summary_history_neg:
            st.session_state.summary_history_neg.remove(summary_instance_dict)

    def add_to_summary_negative():
        summary_instance_dict = {'icon': icon, 'persona': name, 'argument': response, 'color': color}

        # Add or update the instance in summary_history_neg
        if instance_dict not in st.session_state.summary_history_neg:
            st.session_state.summary_history_neg.append(summary_instance_dict)

        # Set usr_rating to -1 or toggle to 0 if already -1
        print(instance_dict.get('usr_rating'))
        if instance_dict.get('usr_rating') != -1:
            instance_dict['usr_rating'] = -1
        else:
            instance_dict['usr_rating'] = 0
            while summary_instance_dict in st.session_state.summary_history_neg:
                st.session_state.summary_history_neg.remove(summary_instance_dict)

        # Remove from summary_history_pos if present
        while summary_instance_dict in st.session_state.summary_history_pos:
            st.session_state.summary_history_pos.remove(summary_instance_dict)

    col3, col1, col2 = st.columns([0.1 ,10, 1], gap="small")
    with col1:
        with st.chat_message(icon):
            msg = f"**:{color}[{name}]:**\n{response}"
            st.markdown(msg)
    with col2:
        up, down = st.columns([1, 1], gap='small')
        with up:
            # Generate a unique key for the button
            unique_key_up = f'upvote_{name}_{response}_{uuid.uuid4()}'
            st.button("👍", key=unique_key_up, on_click=add_to_summary_positive)

        with down:
            # Generate a unique key for the button
            unique_key_down = f'downvote_{name}_{response}_{uuid.uuid4()}'
            st.button("👎", key=unique_key_down, on_click=add_to_summary_negative)
    with col3:
        if instance_dict['usr_rating'] == 1:
            st.write("👍")
        elif instance_dict['usr_rating'] == -1:
            st.write("👎")
