import streamlit as st
import yaml

import llm

DEFAULT_CFG_PATH = './default.yaml'


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
    topic_options = cfg['prompts']['topics']
    topic_id = -1
    if 'topic_id' in st.query_params:
        topic_id = int(st.query_params['topic_id'])

    topic = st.selectbox(label="What topic would you like to learn about?", options=topic_options, index=topic_id if topic_id != -1 else None, label_visibility='hidden')

    if topic is not None:
        st.query_params['topic_id'] = topic_options.index(topic)
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
        st.session_state.agents = llm.generate_personas(topic, 2, cfg)
        st.rerun()

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
                col1, col2, col3 = st.columns([0.2, 4, 0.5], gap="small")
                potential_next_round_button = st.empty()
                # Checkbox to the left of the expander, indicating participation
                with col1:
                    participate = st.checkbox(f'agent_{i}_checkbox', key=f'agent_{i}_checkbox',
                                              label_visibility='collapsed')
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
                        new_title = st.text_input(f"title_{i}", label_visibility='hidden', value=agent.title,
                                                  placeholder="Title")
                        new_description = st.text_area(f"Description_{i}",
                                                       label_visibility='hidden', value=agent.desc,
                                                       placeholder="Description")

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
                    if st.button("🗑️", key=f'remove_{i}'):
                        if agent in st.session_state['participating_agents']:
                            st.session_state['participating_agents'].remove(agent)
                        if agent in st.session_state['agents']:
                            st.session_state['agents'].remove(agent)
                        st.rerun()

        col1, col2 = st.columns([0.5, 0.5], gap='small')

        with col1:

            if st.button("Add agent"):
                st.session_state['agents'].append(llm.add_persona(topic, st.session_state.agents, cfg))
                st.rerun()

        with col2:
            if st.button("Overwrite with AI generated agents"):
                st.session_state.agents = llm.generate_personas(topic, len(st.session_state['agents']), cfg)
                st.session_state.participating_agents = []
                st.rerun()
        st.divider()

        next_round_button = st.button("Start Next Round Debate")

    if 'current_debate_round' not in st.session_state:
        st.session_state['current_debate_round'] = -1

    if 'debate_history' not in st.session_state:
        st.session_state['debate_history'] = {}

    if 'summary_history_pos' not in st.session_state:
        st.session_state['summary_history_pos'] = []

    if 'summary_history_neg' not in st.session_state:
        st.session_state['summary_history_neg'] = []

    if next_round_button or st.session_state['current_debate_round'] > -1:
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
            if next_round_button:
                st.session_state['current_debate_round'] = st.session_state['current_debate_round'] + 1
            with st.spinner(f"Debating on round {st.session_state.current_debate_round + 1}..."):
                rounds = [f"Round {i + 1}" for i in range(st.session_state['current_debate_round'] + 1)] + ['Summary']
                print(rounds)
                round_tabs = st.tabs(rounds)
                for i in range(st.session_state.current_debate_round if next_round_button else st.session_state.current_debate_round + 1):
                    with round_tabs[i]:
                        for chat_msg in st.session_state.debate_history[i]:
                            llm.write_message(chat_msg['icon'], chat_msg['persona'], chat_msg['argument'])
                if next_round_button:
                    with round_tabs[st.session_state['current_debate_round']]:
                        sorted_participating_agents = sorted(st.session_state['participating_agents'],
                                                             key=lambda obj: st.session_state['agents'].index(obj))
                        last_round_history = st.session_state['debate_history'].get(st.session_state['current_debate_round'] - 1, [])
                        st.session_state['debate_history'][st.session_state['current_debate_round']] = llm.debate_round(topic, sorted_participating_agents, cfg, last_round_history)

                with round_tabs[-1]:
                    for chat_msg in remove_duplicates_by_repr(st.session_state.summary_history_pos):
                        col1, col2 = st.columns([10, 1], gap="small")
                        with col1:
                            with st.chat_message(chat_msg['icon']):
                                st.markdown(f"**{chat_msg['persona']}:**\n{chat_msg['argument']}")
                        with col2:
                            if st.button("🗑️", key=f"remove_{chat_msg['persona']}_{chat_msg['argument']}"):
                                if chat_msg in st.session_state.summary_history_pos:
                                    st.session_state.summary_history_pos = [d for d in st.session_state.summary_history_pos if d != chat_msg]
                                st.rerun()
                    st.divider()
                    for chat_msg in remove_duplicates_by_repr(st.session_state.summary_history_neg):
                        col1, col2 = st.columns([10, 1], gap="small")
                        with col1:
                            with st.chat_message(chat_msg['icon']):
                                st.markdown(f"**{chat_msg['persona']}:**\n{chat_msg['argument']}")
                        with col2:
                            if st.button("🗑️", key=f"remove_{chat_msg['persona']}_{chat_msg['argument']}"):
                                if chat_msg in st.session_state.summary_history_neg:
                                    st.session_state.summary_history_neg = [d for d in st.session_state.summary_history_neg if d != chat_msg]
                                st.rerun()


def remove_duplicates_by_repr(dicts):
    seen_reprs = set()
    unique_dicts = []
    for d in dicts:
        repr_d = repr(d)
        if repr_d not in seen_reprs:
            seen_reprs.add(repr_d)
            unique_dicts.append(d)
    return unique_dicts

if __name__ == '__main__':
    main()
