import streamlit as st
import yaml
from streamlit_searchbox import st_searchbox
import llm

DEFAULT_CFG_PATH = './default.yaml'


def main():
    # Pre-Configuration
    st.set_page_config(page_title="Persona Debate", page_icon=None, layout="wide", initial_sidebar_state="expanded", menu_items={'About': "This interface is part of an ongoing research project at the University of Texas at Austin, exploring decision-support through balanced information presentation. The content provided is for informational purposes only and does not constitute advice. The University of Texas at Austin is not liable for any actions taken based on the information provided through this interface. Always exercise judgment and caution when making decisions."})
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
    not_preselected = False
    if 'topic_id' in st.query_params:
        topic_id = int(st.query_params['topic_id'])
        topic = topic_options[topic_id]
    elif 'topic' in st.query_params:
        topic = st.query_params['topic']
    else:
        not_preselected = True
        # This function will be called on user input to generate autocomplete suggestions
        def search_topics(searchterm: str):
            # Filter for matching topic options or return the full list if search term is empty
            return [topic for topic in topic_options if searchterm.lower() in topic.lower()] + [searchterm]

        # Integrate the search box with autocomplete in your app
        topic_inp = st_searchbox(
            search_function=search_topics,
            placeholder="Type to search for topics or enter your own...",
            default_options=topic_options,  # This will show all topics when the user clicks on the search box
            clear_on_submit=False,  # Set to True if you want the box to clear after submission
            rerun_on_update=True,  # This will rerun the app and update suggestions based on the latest user input
            key="topic_searchbox"
        )
        topic = topic_inp
    if topic is not None and topic not in topic_options:
        st.query_params['topic'] = topic
    elif topic is not None and topic in topic_options:
        st.query_params['topic_id'] = topic_options.index(topic)
    # Set the title based on whether the user has input something or not
    with title:
        if topic:
            st.title(topic, help="This interface is part of an ongoing research project at the University of Texas at Austin, exploring decision-support through balanced information presentation. The content provided is for informational purposes only and does not constitute advice. The University of Texas at Austin is not liable for any actions taken based on the information provided through this interface. Always exercise judgment and caution when making decisions.")
            if not_preselected:
                del topic_inp
        else:
            st.title("Choose a topic to uncover balanced insights and inform your understanding.", help="This interface is part of an ongoing research project at the University of Texas at Austin, exploring decision-support through balanced information presentation. The content provided is for informational purposes only and does not constitute advice. The University of Texas at Austin is not liable for any actions taken based on the information provided through this interface. Always exercise judgment and caution when making decisions.")
            return
    num_personas_start = cfg['debate_params']['num_personas']

    # Set up agents, make some blank personas for now...
    if 'agents' not in st.session_state:
        st.session_state.agents = llm.generate_personas(topic, cfg['debate_params']['num_personas'], cfg)
        st.rerun()

    # List of indices from generated_agents of the Agents in the debate
    if 'participating_agents' not in st.session_state:
        st.session_state['participating_agents'] = []



    next_round_button = None

    colors = ['blue', 'green', 'orange', 'red', 'violet', 'gray', 'rainbow']
    color_emojis = ['🔵', '🟢', '🟠', '🔴', '🟣', '⚪', '🌈']

    with st.sidebar:
        st.title("Personas in Debate", help="Pick and customize various perspectives on the given topic.")
        st.divider()
        for i, agent in enumerate(st.session_state.agents):
            agent_title, agent_desc = agent.title, agent.desc
            with st.container():
                agent_title_placeholder = st.empty()
                col1, col2, col3 = st.columns([0.2, 4, 0.5], gap="small")
                potential_next_round_button = st.empty()
                agent.color = colors[i % len(colors)]
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
                            st.write(f"Persona {idx + 1}")

                    else:
                        if agent in st.session_state['participating_agents']:
                            st.session_state['participating_agents'].remove(agent)


                with col2:
                    name = f":{agent.color}[{agent.emoji + ' ' + agent_title.title()}]"
                    with st.expander(name, agent._recently_expanded):
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



        if st.button("Add persona"):
            st.session_state['agents'].append(llm.add_persona(topic, st.session_state.agents, cfg))
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
            with st.spinner(f"Currently debating for Round {st.session_state.current_debate_round + 1}"):
                rounds = [f"Round {i + 1}" for i in range(st.session_state['current_debate_round'] + 1)] + ['Summary']
                print(rounds)
                round_tabs = st.tabs(rounds)
                for i in range(st.session_state.current_debate_round if next_round_button else st.session_state.current_debate_round + 1):
                    with round_tabs[i]:
                        for chat_msg in st.session_state.debate_history[i]:
                            llm.write_message(chat_msg['icon'], chat_msg['persona'], chat_msg['argument'], chat_msg['color'])


                with round_tabs[-1]:
                    pos_col, neg_col = st.columns([1, 1])
                    with pos_col:
                        st.header("👍 Agree")
                        st.divider()
                        for chat_msg in remove_duplicates_by_repr(st.session_state.summary_history_pos):
                            col1, col2 = st.columns([10, 1], gap="small")
                            with col1:
                                with st.chat_message(chat_msg['icon']):
                                    color = chat_msg['color']
                                    msg = f"**:{color}[{chat_msg['persona']}]:**\n{chat_msg['argument']}"


                                    st.markdown(msg)
                            with col2:
                                if st.button("🗑️", key=f"remove_{chat_msg['persona']}_{chat_msg['argument']}"):
                                    if chat_msg in st.session_state.summary_history_pos:
                                        st.session_state.summary_history_pos = [d for d in st.session_state.summary_history_pos if d != chat_msg]
                                    st.rerun()
                    with neg_col:
                        st.header("👎 Disagree")
                        st.divider()
                        for chat_msg in remove_duplicates_by_repr(st.session_state.summary_history_neg):
                            col1, col2 = st.columns([10, 1], gap="small")
                            with col1:
                                with st.chat_message(chat_msg['icon']):
                                    color = chat_msg['color']
                                    msg = f"**:{color}[{chat_msg['persona']}]:**\n{chat_msg['argument']}"
                                    st.markdown(msg)
                            with col2:
                                if st.button("🗑️", key=f"remove_{chat_msg['persona']}_{chat_msg['argument']}"):
                                    if chat_msg in st.session_state.summary_history_neg:
                                        st.session_state.summary_history_neg = [d for d in st.session_state.summary_history_neg if d != chat_msg]
                                    st.rerun()

                if next_round_button:
                    with round_tabs[st.session_state['current_debate_round']]:
                        st.empty()
                        sorted_participating_agents = sorted(st.session_state['participating_agents'],
                                                             key=lambda obj: st.session_state['agents'].index(obj))
                        last_round_history = st.session_state['debate_history'].get(st.session_state['current_debate_round'] - 1, [])
                        st.session_state['debate_history'][st.session_state['current_debate_round']] = llm.debate_round(topic, sorted_participating_agents, cfg, last_round_history)


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
