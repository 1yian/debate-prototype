import streamlit as st
import yaml
from streamlit_option_menu import option_menu

import llm

DEFAULT_CFG_PATH = './default.yaml'


def move_element(lst, index, direction):
    if direction == 'right' and index < len(lst) - 1:
        lst[index], lst[index + 1] = lst[index + 1], lst[index]
    elif direction == 'left' and index > 0:
        lst[index], lst[index - 1] = lst[index - 1], lst[index]
    return lst


def main():
    # Pre-Configuration
    st.set_page_config(layout="wide")
    # Some unfortunate CSS that's needed for alignment
    st.markdown("""
        <style>
            /* Targets the outer container  */
            .row-widget.stCheckbox {
                margin-top: 10px;  /* Adjust this margin value */
            }
            .row-widget.stButton {
                margin-top: 3px;
            }
        </style>
    """, unsafe_allow_html=True)
    with open(DEFAULT_CFG_PATH, 'r') as tmp_fd:
        cfg = yaml.safe_load(tmp_fd)

    # First page user sees - deciding which topic to chose
    title = st.empty()
    topic = st.text_input("topic", placeholder="Can alternative energy effectively replace fossil fuels?",
                          label_visibility='hidden')

    # Set the title based on whether the user has input something or not
    with title:
        if topic:
            st.title(topic)
        else:
            st.title("Hello! What topic would you like to learn more about today?")
            return
    num_personas_start = cfg['debate_params']['num_personas']

    # Set up agents, make some blank personas for now...
    if 'agents' not in st.session_state:
        st.session_state['agents'] = [llm.Agent('', '', '') for _ in range(num_personas_start)]

    # List of indices from generated_agents of the Agents in the debate
    if 'participating_agents' not in st.session_state:
        st.session_state['participating_agents'] = []

    next_round_button = None

    with st.sidebar:
        st.title("Agents in Debate", help="This is a debate :D")
        st.divider()
        for i, agent in enumerate(st.session_state.agents):
            agent_title, agent_desc = agent.title, agent.desc
            with st.container():
                agent_title_placeholder = st.empty()
                col1, col2, col3, col4, col5 = st.columns([0.2, 3, 0.5, 0.5, 0.5], gap="small")
                potential_next_round_button = st.empty()
                # Checkbox to the left of the expander, indicating participation
                with col1:
                    participate = st.checkbox(f'agent_{i}_checkbox', key=f'agent_{i}_checkbox', label_visibility='collapsed')
                    if participate:
                        if agent not in st.session_state['participating_agents']:
                            st.session_state['participating_agents'].append(agent)

                        sorted_participating_agents = sorted(st.session_state['participating_agents'],
                                                             key=lambda obj: st.session_state['agents'].index(obj))
                        idx = sorted_participating_agents.index(agent)
                        with agent_title_placeholder:
                            st.write(f"Agent {idx + 1}")
                    else:
                        if agent in st.session_state['participating_agents']:
                            st.session_state['participating_agents'].remove(agent)

                with col2:
                    with st.expander(agent_title.title(), agent._recently_expanded):
                        # Text area for editing description, shown only when the expander is open
                        new_title = st.text_input(f"title_{i}",label_visibility='hidden', value=agent.title, placeholder="Title")
                        new_description = st.text_area(f"Description_{i}",
                                                       label_visibility='hidden', value=agent.desc, placeholder="Description")

                        if agent.desc != new_description:
                            agent.desc = new_description
                            agent._recently_expanded = True
                        elif agent.title != new_title:
                            agent.title = new_title
                            agent._recently_expanded = True
                            st.rerun()
                        else:
                            agent._recently_expanded = False

                with col3:
                    if st.button("⬆️", key=f'up_{i}'):
                        lst = st.session_state['agents']
                        st.session_state['agents'] = move_element(lst, i, 'left')
                        st.rerun()

                with col4:
                    if st.button("⬇️", key=f'down_{i}'):
                        lst = st.session_state['agents']
                        st.session_state['agents'] = move_element(lst, i, 'right')
                        st.rerun()

                with col5:
                    if st.button("🗑️", key=f'remove_{i}'):
                        if agent in st.session_state['participating_agents']:
                            st.session_state['participating_agents'].remove(agent)
                        if agent in st.session_state['agents']:
                            st.session_state['agents'].remove(agent)
                        st.rerun()

        col1, col2 = st.columns([0.5, 0.5], gap='small')

        with col1:

            if st.button("Add agent"):
                st.session_state['agents'].append(llm.Agent("", ""))
                st.rerun()

        with col2:
            if st.button("Overwrite with AI generated agents"):
                st.session_state.agents = llm.generate_personas(topic, len(st.session_state['agents']), cfg)
                st.rerun()
        st.divider()


        next_round_button = st.button("Start Next Round Debate")
    if 'current_debate_round' not in st.session_state:

        st.session_state['current_debate_round'] = -1
    if next_round_button:
        if len(st.session_state['participating_agents']) == 0:
            st.error("Error: No agents selected!")
        elif len(st.session_state['participating_agents']) == 1:
            st.error("Error: Please select more than 1 agent!")
        else:
            for agent in st.session_state['participating_agents']:
                if len(agent.title) == 0:
                    st.warning(f"Warning: {agent.title} does not have a title!")
                if len(agent.desc) == 0:
                    st.warning(f"Warning: {agent.title} does not have a description!")
            st.success("Starting debate!")
            st.session_state['current_debate_round'] = st.session_state['current_debate_round'] + 1
            rounds = [f"Round {i}" for i in range(cfg['debate_params']['num_debate_rounds'])]
            round_tabs = st.tabs(rounds)
            with round_tabs[st.session_state['current_debate_round']]:
                sorted_participating_agents = sorted(st.session_state['participating_agents'],
                                                     key=lambda obj: st.session_state['agents'].index(obj))
                st.session_state['debate_history'] = llm.debate_round(topic, sorted_participating_agents, cfg)


if __name__ == '__main__':
    main()