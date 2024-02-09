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
                'Persona Generation Prompt '
                '(Use [TOPIC], [NUM_PERSONAS] in the prompt)',
                cfg['prompts']['persona_creation'],
            )

        cfg['prompts']['debate_start'] = \
            st.text_area(
                'Starting Round Debate Prompt '
                '(Use [TOPIC], [NAME], [DESC], [LIMITER] in the prompt)',
                cfg['prompts']['debate_start'],
            )

        cfg['prompts']['debate'] = \
            st.text_area(
                'Regular Debate Prompt'
                '(Use [TOPIC], [NAME], [DESC], [HISTORY], [LIMITER] in the prompt)',
                cfg['prompts']['debate'],
            )

        cfg['prompts']['response_length'] = \
            st.text_input(
                "Response 'limiter' Prompt (use [RESPONSE_LENGTH] in the prompt)",
                cfg['prompts']['response_length']
            )
    with st.sidebar.expander('Debate Settings', expanded=True):
        cfg['debate_params']['response_length'] = \
            st.text_input(
                "Desired Response Length from Debaters (eg. '5 sentences')",
                placeholder='Not set',
                value=cfg['debate_params']['response_length']
            )

        cfg['debate_params']['limit_response_length'] = cfg['debate_params']['response_length'] is not None

        # TODO Come up with a better name than 'continuous mode'
        cfg['debate_params']['enable_continuous_mode'] = \
            st.toggle(
                'Continuous Mode',
                cfg['debate_params']['enable_continuous_mode']
            )

        cfg['debate_params']['transcript_word_limit'] = \
            st.number_input(
                'Transcript summarization threshold (words)',
                value=cfg['debate_params']['transcript_word_limit'],
                step=100,
                min_value=100,
                max_value=512_000,
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


def draw_personas(personas):
    for i, persona in enumerate(personas):
        persona['name'] = st.text_input(
            f"Persona {i}",
            value=persona['name'],
            placeholder="Enter persona name here. For example, 'Dr. John Smith' or 'Doctor'",
            key=f"persona_{i}_name"
        )
        persona['description'] = st.text_area(
            label='',
            value=persona['description'],
            placeholder="Optional. Enter persona description here. For example, 'Believes that vaccines cause autism.'",
            key=f"persona_{i}_description",
            label_visibility="collapsed"
        )


def add_persona():
    # Add a new, empty persona
    st.session_state.generated_personas.append({'name': '', 'description': ''})
    print(len(st.session_state.generated_personas))


def remove_persona():
    # Remove the last persona if more than one exists
    if len(st.session_state.generated_personas) > 1:
        st.session_state.generated_personas.pop()


if __name__ == '__main__':
    # Load the default config from default.yaml
    with open(DEFAULT_CFG_PATH, 'r') as tmp_fd:
        cfg = yaml.safe_load(tmp_fd)

    # Define the initial layout of the website
    st.title('Debate Simulation')
    reset = st.button('Reset')
    status_message = st.sidebar.empty()
    draw_sidebar(cfg)

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

    with top_container:
        if 'generated_personas' not in st.session_state:
            st.session_state.generated_personas = [{'name': '', 'description': ''} for _ in range(2)]

        with persona_tab:
            # Draw the add and remove buttons
            # Create two columns for the buttons
            col1, col2, col3 = st.columns(3)

            # Place the add button in the first column
            with col1:
                st.button("Add Persona", on_click=add_persona)

            # Place the remove button in the second column
            with col2:
                st.button("Remove Persona", on_click=remove_persona)

            with col3:
                if topic:
                    gen = st.button("Generate Personas Instead")
                    if gen:
                        st.session_state.generated_personas = llm.generate_personas(topic,
                                                                                    len(st.session_state.generated_personas),
                                                                                    cfg)

            # Draw the personas
            draw_personas(st.session_state.generated_personas)

        if cfg['ux_params']['show_persona_desc'] and 'generated_personas' in st.session_state:
            picked_personas = st.multiselect(
                'Pick personas to include in debate (in order):',
                [persona['name'] for persona in st.session_state.generated_personas],
            )
            if 'picked_personas' not in st.session_state:
                st.session_state.picked_personas = []
            for persona in picked_personas:
                for tmp_persona in st.session_state.generated_personas:
                    if tmp_persona['name'] == persona:
                        st.session_state.picked_personas.append(tmp_persona)
                        break

        if 'picked_personas' in st.session_state and len(st.session_state.picked_personas) > 2:
            col1, col2 = st.columns(2)
            with col1:
                start = st.button('Start debate')
            with col2:
                stop = st.button('Stop debate')

            if stop:
                st.stop()

            if start and 'picked_personas' in st.session_state:
                with st.spinner('Debate in progress...'):
                    with debate_tab:
                        llm.simulate_debate(topic, st.session_state.picked_personas, cfg)
