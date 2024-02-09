import streamlit as st
from streamlit_option_menu import option_menu

import streamlit as st
from collections import namedtuple

# Step 2: Define the namedtuple with specified keys
Agent = namedtuple('Agent', ['title', 'description', 'emoji'])

# Set up the page configuration
st.set_page_config(layout="wide")
title = st.empty()
# Main header in the main page
topic = st.text_input("topic", placeholder="Can alternative energy effectively replace fossil fuels?", label_visibility='hidden')
if topic:
    with title:
        st.title(topic)
else:
    with title:
        st.title("Hello! What topic would you like to learn more about today?")
        exit()


# Define the default descriptions for each agent
agent_dict = [
    Agent("Environmentalist", "A staunch supporter of renewable energy and sustainable practices.", "🌱"),
Agent("Environmentalist", "A staunch supporter of renewable energy and sustainable practices.", "🌱"),
Agent("Environmentalist", "A staunch supporter of renewable energy and sustainable practices.", "🌱"),
    Agent("Economic Transition Analyst", "An economic analyst considering the impacts of energy transitions.", "💵"),
    Agent("Coal Industry Defender", "A spokesperson for the coal industry who believes coal is irreplaceable in the energy sector.", "⛏️"),
]
st.markdown("""
<style>
.st-ca {  /* Targets the sidebar checkbox container */
    margin-top: 16px; /* Adjust this value to set the top margin */
}
.st-bn {  /* Targets the sidebar checkbox container */
    margin-top: 16px; /* Adjust this value to set the top margin */
}
</style>
""", unsafe_allow_html=True)
# Initialize the session state for agent participation if it does not exist
for i, _ in enumerate(agent_dict):
    if f'participate_{i}' not in st.session_state:
        st.session_state[f'participate_{i}'] = False  # Default to True if you want all agents to participate initially

participating_agents = []
# Sidebar for agents' selection with fixed personas and editable descriptions
with st.sidebar:
    st.header("Agents in Debate", help="This is a debate :D", divider='gray')
    for i, (agent_name, agent_desc, _) in enumerate(agent_dict):

        title_placeholder = st.empty()
        ##st.markdown(f"**{agent_name}**")  # You can use st.markdown for styling
        # Check if there's already a description in the session state, otherwise use default
        description_key = f'description_{i}'
        if description_key not in st.session_state:
            st.session_state[description_key] = agent_desc

        # Use a container to ensure that the layout is consistent
        with st.container():
            # Create an expander to edit the description
            title_placeholder = st.empty()
            col1, col2 = st.columns([0.5, 4], gap="small")

            # Checkbox to the left of the expander, indicating participation
            with col1:
                participate = st.checkbox("", key=f'participate_{i}')
                if participate:
                    participating_agents.append(i)
                    with title_placeholder:
                        st.write(f"Agent {participating_agents.index(i) + 1}")
                else:
                    if i in participating_agents:
                        participating_agents.remove(i)



            # Expander for the agent description
            with col2:
                with st.expander(agent_name.title()):
                    # Text area for editing description, shown only when the expander is open
                    new_description = st.text_area("Description",
                                                   key=description_key, label_visibility='hidden')

    st.divider()
    if st.button("Start Next Round Debate"):
        if len(participating_agents) == 0:
            st.error("Error: No agents selected!")
        elif len(participating_agents) == 1:
            st.error("Error: Please select more than 1 agent!")
        else:
            for agent_idx in participating_agents:
                if len(st.session_state[f'description_{agent_idx}']) == 0:
                    st.warning(f"Warning: {agent_dict[agent_idx][0]} does not have a description!")
                    break
            st.success("Starting debate!")



# Main page content
# Rounds navigation
rounds = ["Round 1", "Round 2", "Round 3", "Summary"]
selected_round = option_menu(menu_title="", options=rounds, orientation="horizontal")
a1_text = """Ladies and gentlemen, I stand before you as a staunch supporter of our planet's future...
            The transition to renewable energy is a pivotal step in this direction."""
a2_text = """Dr. Green presents a compelling case for the environmental imperatives of alternative energy...
            An abrupt shift could lead to economic disruptions."""
a3_text = """I appreciate the insights shared by Dr. Green and The Economist. However, I must emphasize that coal...
            We cannot overlook the role of coal in meeting our current and future energy demands."""

# Debate content for each agent
if selected_round == "Round 1":
    st.subheader("Round 1")
    # The expanders for each agent's argument
    with st.chat_message('Coal Industry Defender', avatar='⛏️'):
        st.markdown('Coal Industry Defender: I love coal!')

# Add similar blocks for Round 2, Round 3, and Summary

# Run the streamlit app in your terminal using: streamlit run your_script.py
