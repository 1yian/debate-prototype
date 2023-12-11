import openai
import json
from summarizer.sbert import SBertSummarizer
import os
OPENAI_KEY = os.environ.get('OPENAI_KEY')
PERSONA_GEN_PROMPT = (
        f"Given the topic [TOPIC], create a roundtable debate of different personas "
        f"to expertly show key perspectives on the issue. Output the personas as a list "
        f"of JSON objects. Each JSON object should have the following structure: "
        f"{{'name': 'Name of the Persona',"
        f"'description': 'Brief Description of the Persona'}}. Ensure that the output is "
        f"formatted as valid JSON. Please generate exactly [NUM_PERSONAS] personas."
        )
START_DEBATE_PROMPT = (f"You are in a roundtable debate on the topic [TOPIC]. "
          f"You are [NAME], who is [DESC]. "
          f"Please start the debate by concisely presenting your argument for your stance on the topic.")
DEBATE_PROMPT = (f"You are in a continuing roundtable debate on the topic [TOPIC]. "
          f"You are [NAME], who is [DESC]. "
          f"Here is the transcript of the debate so far: [HISTORY] "
          f"Please continue to debate the others, concisely supporting your stance on the topic.")
SHORTEN_AFTER = 2500
TEMPERATURE = 0.7
# Function to call OpenAI's API
def call_openai(prompt, temperature=0.7):
    openai.api_key = OPENAI_KEY
    pa_prompt = [
        {"role": "user",
         "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=pa_prompt,
        temperature=temperature,
    )
    return response.choices[0].message['content'].strip()

# Step 1: User Input for Debate Topic
def get_debate_topic():
    return input("Enter a debate topic: ")

# Step 2: Persona Generation
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


def generate_personas(topic):
    prompt = PERSONA_GEN_PROMPT
    prompt = prompt.replace("[TOPIC]", topic).replace("[NUM_PERSONAS]", str(int(NUM_PERSONAS)))
    response = call_openai(prompt, TEMPERATURE)
    return extract_json_from_response(response)



# Step 3: Debate Simulation
model = SBertSummarizer('paraphrase-MiniLM-L6-v2')
def check_shorten(debate_history):
    num_words = len(str(debate_history).split())
    if num_words > SHORTEN_AFTER:
        print("SHORTENING...")
        ratio = (SHORTEN_AFTER - 100) / num_words
        new_debate_history = []
        for line in debate_history:
            line = line.copy()
            new_debate_history.append(model(line['argument'], ratio))
    else:
        print("NOT SHORTENING...", num_words)
        new_debate_history = debate_history
    return new_debate_history

import streamlit as st
st.set_page_config(layout="wide")
from summarizer.sbert import SBertSummarizer
status_message = st.sidebar.empty()
model = SBertSummarizer('paraphrase-MiniLM-L6-v2')

def simulate_debate(topic, personas, rounds=3):
    debate_history = []
    print("here")
    for i in range(int(rounds)):
        for persona in personas:
            status_message.text(f"On debate round {i + 1}, generating for {persona['name']}")
            prompt = START_DEBATE_PROMPT if len(debate_history) == 0 else DEBATE_PROMPT
            str_debate = str(check_shorten(debate_history))
            prompt = prompt.replace("[TOPIC]", topic).replace("[NAME]", persona['name']).replace("[DESC]", persona['description']).replace("[HISTORY]", str_debate)
            response = call_openai(prompt, TEMPERATURE)

            # Streamlit chat message
            with st.chat_message(persona['name']):
                st.write(f"{persona['name']}:\n", response)

            debate_history.append({"persona": persona['name'], "argument": response})

def display_personas(personas):
    st.subheader("Generated Personas")
    for persona in personas:
        with st.expander(persona['name']):
            st.write(persona['description'])

def main():
    st.title("Roundtable Debate Simulation")

    # Allow users to modify parameters
    global OPENAI_KEY, PERSONA_GEN_PROMPT, START_DEBATE_PROMPT, DEBATE_PROMPT, SHORTEN_AFTER, NUM_ROUNDS, TEMPERATURE, NUM_PERSONAS, MODEL_NAME
    PERSONA_GEN_PROMPT = st.sidebar.text_area("Persona Generation Prompt \n(Use [TOPIC], [NUM_PERSONAS] in your prompt)", PERSONA_GEN_PROMPT)
    START_DEBATE_PROMPT = st.sidebar.text_area("Start Debate Prompt \n(Use [TOPIC], [NAME], [DESC] in your prompt)", START_DEBATE_PROMPT)
    DEBATE_PROMPT = st.sidebar.text_area("Debate Prompt \n(Use [TOPIC], [NAME], [DESC], [HISTORY] in your prompt)", DEBATE_PROMPT)
    SHORTEN_AFTER = st.sidebar.number_input("Shorten after (Max word length of debate transcript before we summarize)", value=SHORTEN_AFTER, step=100)
    NUM_PERSONAS = st.sidebar.number_input("Number of personas", value=4, step=1)
    NUM_ROUNDS = st.sidebar.number_input("Number of debate rounds", value=1, step=1)
    TEMPERATURE = st.sidebar.number_input("Temperature (for GPT)", value=0.7, step=0.1)
    MODEL_NAME = st.sidebar.selectbox("GPT Model:", ['gpt-4', 'gpt-3.5-turbo'])
    status_message.text("Waiting for topic...")
    topic = st.text_input("Enter a debate topic: ")

    if topic:
        status_message.text("Generating personas...")
        personas = generate_personas(topic)
        display_personas(personas)
        status_message.text("Starting debate...")
        simulate_debate(topic, personas, NUM_ROUNDS)

if __name__ == "__main__":
    main()
