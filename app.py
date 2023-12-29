import streamlit as st
import yaml

from llm import call_llm, SUPPORTED_MODELS
import llm
DEFAULT_CFG_PATH = './default.yaml'


def draw_sidebar(cfg):
    cfg['ux_params']['show_persona_desc'] = \
        st.sidebar.toggle(
            "Show personas",
            cfg['ux_params']['show_persona_desc']
        )

    with st.sidebar.expander('Prompts:'):

        cfg['prompts']['persona_creation'] = \
            st.text_area(
                'Persona Generation Prompt\n'
                '(Use [TOPIC], [NUM_PERSONAS] in the prompt)',
                cfg['prompts']['persona_creation'],
            )

        cfg['prompts']['debate_start'] = \
            st.text_area(
                'Starting Round Debate Prompt\n'
                '(Use [TOPIC], [NAME], [DESC] in the prompt)',
                cfg['prompts']['debate_start'],
            )

        cfg['prompts']['debate'] = \
            st.text_area(
                'Regular Debate Prompt\n'
                '(Use [TOPIC], [NAME], [DESC], [HISTORY] in the prompt)',
                cfg['prompts']['debate'],
            )
    with st.sidebar.expander('Debate Settings', expanded=True):
        cfg['debate_params']['enable_continuous_mode'] = \
            st.toggle(
                'Continuous Mode',
                cfg['debate_params']['enable_continuous_mode']
            )

        cfg['debate_params']['generate_personas'] = \
            st.toggle(
                'Generate personas', cfg['debate_params']['generate_personas']
            )

        cfg['debate_params']['transcript_word_limit'] = \
            st.number_input(
                'Transcript summarization threshold (words)',
                value=cfg['debate_params']['transcript_word_limit'],
                step=100,
                min_value=100,
                max_value=512_000,
            )
        cfg['debate_params']['num_personas'] = \
            st.number_input(
                'Number of personas to generate',
                value=cfg['debate_params']['num_personas'],
                step=1,
                min_value=2,
                max_value=150,
            )
        cfg['debate_params']['num_debate_rounds'] = \
            st.number_input(
                'Number of debate_rounds',
                value=cfg['debate_params']['num_debate_rounds'],
                step=1,
                min_value=1,
                max_value=50
            )

    with st.sidebar.expander('LLM Params (limited for now):'):

        cfg['llm_params']['model_name'] = \
            st.selectbox('Model', SUPPORTED_MODELS)

        cfg['llm_params']['temperature'] = \
            st.number_input(
                'Temperature',
                value=cfg['llm_params']['temperature'],
                step=0.1,
                min_value=0.0,
                max_value=2.0,
            )

def draw_personas(personas, persona_tab):
    for i, persona in enumerate(personas):
        persona['name'] = st.text_input(
            f"Persona {i} Name",
            value=persona['name'],
            placeholder="Enter persona name here."
                        " For example, 'Dr. John Smith' or 'Doctor'",
            label_visibility='collapsed'
        )

        persona['description'] = st.text_area(
            f"Persona {i} Description",
            value=persona['description'],
            placeholder="Enter persona description here."
                        " For example, 'Believes that vaccines cause autism.'",
            label_visibility='collapsed'
        )

if __name__ == '__main__':
    # Load the default config from default.yaml
    with open(DEFAULT_CFG_PATH, 'r') as tmp_fd:
        cfg = yaml.safe_load(tmp_fd)

    # Define the initial layout of the website
    st.title('Debate Simulation')
    reset = st.button('Reset')
    status_message = st.sidebar.empty()
    draw_sidebar(cfg)
    status_message.text('Waiting for topic...')

    # Reset the experiment
    if reset:
        for key in st.session_state.keys():
            del st.session_state[key]

    # Get a topic from the user.
    topic = st.text_input("Topic", placeholder='Enter a debate topic: ')

    top_container = st.container()

    # Define two tabs- personas and debate
    # TODO Remove the tab if we aren't showing personas
    persona_tab, debate_tab = st.tabs(["Personas", "Debate"])


    if topic:
        with top_container:
            if not 'personas' in st.session_state:
                with st.spinner('Generating personas...'):
                    personas = llm.generate_personas(topic, cfg)
                    st.session_state['personas'] = personas


            if cfg['ux_params']['show_persona_desc'] and 'personas' in st.session_state:
                with persona_tab:
                    draw_personas(st.session_state.personas, persona_tab)
            start = st.button('Start debate...')
            stop = st.button('Stop debate...')

            if stop:
                st.stop()

            if start and 'personas' in st.session_state:
                with st.spinner('Debate in progress...'):
                    with debate_tab:
                        llm.simulate_debate(topic, st.session_state.personas, cfg)
