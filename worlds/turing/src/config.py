"""
       █████  █████ ██████   █████           █████ █████   █████ ██████████ ███████████    █████████  ██████████
      ░░███  ░░███ ░░██████ ░░███           ░░███ ░░███   ░░███ ░░███░░░░░█░░███░░░░░███  ███░░░░░███░░███░░░░░█
       ░███   ░███  ░███░███ ░███   ██████   ░███  ░███    ░███  ░███  █ ░  ░███    ░███ ░███    ░░░  ░███  █ ░
       ░███   ░███  ░███░░███░███  ░░░░░███  ░███  ░███    ░███  ░██████    ░██████████  ░░█████████  ░██████
       ░███   ░███  ░███ ░░██████   ███████  ░███  ░░███   ███   ░███░░█    ░███░░░░░███  ░░░░░░░░███ ░███░░█
       ░███   ░███  ░███  ░░█████  ███░░███  ░███   ░░░█████░    ░███ ░   █ ░███    ░███  ███    ░███ ░███ ░   █
       ░░████████   █████  ░░█████░░████████ █████    ░░███      ██████████ █████   █████░░█████████  ██████████
        ░░░░░░░░   ░░░░░    ░░░░░  ░░░░░░░░ ░░░░░      ░░░      ░░░░░░░░░░ ░░░░░   ░░░░░  ░░░░░░░░░  ░░░░░░░░░░
                 A Collectionless AI Project (https://collectionless.ai)
                 Registration/Login: https://unaiverse.io
                 Code Repositories:  https://github.com/collectionlessai/
                 Main Developers:    Stefano Melacci (Project Leader), Christian Di Maio, Tommaso Guidi
"""


# Generic options to configure the Turing Test Hotel
# All time measures are in SECONDS.
class Config:
    # Optional registration gate. Leave the sheets empty for unrestricted entry.
    # When enabled, set both mappings for human (True) and AI (False) participants.
    # Use plain URLs; form links can include <YOUR_NICKNAME> to prefill the nickname.
    form = {}
    registered_users_form_sheets = {}
    registered_users_form_column_id = 3  # Zero-based nickname column in the registration sheet
    broadcast_when_no_humans = True
    max_message_size = 512  # Set it to <= 0 to disable
    use_letter_names = False
    test_duration = 300  # Seconds (int)
    survey_reply_time = 240  # Seconds (WARNING: do not get too close to 300, since all interactions expire at 300!)
    time_in_voting_booth_before_activating_vote = 3  # Seconds
    moving_time = 10  # Time to move from the floor entrance to the chat table or from the chat table to the voting both
    max_time_in_every_state = (max([test_duration, survey_reply_time, moving_time]) +
                               moving_time + time_in_voting_booth_before_activating_vote + 5)  # Add a gap
    max_guests_per_room = 4
    max_overbooked_guests = 1
    rooms_per_floor = 50
    min_msgs_from_votee = 3  # Minimum number of received messages from somebody to vote hit
    msg_cooldown = 1  # Minimum time between two consecutive messages sent by a guest to the room (anti-flooding)
    max_queued_msgs = 2  # Max messages a guest can keep waiting for the cooldown (the oldest ones get dropped)
    store_conversations = True  # Store the room conversations in the world stats DB
    msg_filter = True  # Mask bad words (and personal data) in the messages broadcast in the rooms
    msg_filter_pii = True  # Also mask e-mails, phone numbers, IBANs, fiscal codes, addresses, links
    msg_filter_max_severe = 5  # Hate speech messages a guest can send before being pushed off the floor
    send_reminder_every = 65  # Reminder on how to exit the room and vote
    skipped_votes_alarm = 3  # Unreadable votes in a row (hotel-wide) that trip the pipeline alarm in the logs
    send_floor_updates_every = 3  # From floor manager to hotel manager
    decompression_time = 90
    disconnect_non_responsive_managers_after = 30  # When "connect" is triggered, time to wait for the handshake
    exit_trigger_message = "exit"  # The message that an agent can write to early stop the conversation and vote
    manager_fake_name = "MANAGER"
    unknown_guest_name = "unk"
    sender_prefix = "**"
    sender_suffix = ":** "  # Do not forget the final space here
    # Separator between the EVENTS batched into one processor input sample (see guest.py's contract).
    # It is the ASCII RECORD SEPARATOR, a character no chat message can contain (the guest strips it from
    # every event before batching), so events keep their internal newlines and splitting is lossless
    event_separator = "\x1e"
    init_message = ("**WELCOME TO THE TURING HOTEL** 🏨\n\n"
                    "This is a hotel of rooms running a multi-agent Turing test, where you are both "
                    "the judge ⚖️ and a conversation partner 🗣️!\n"
                    "You will enter a room with strangers who may be humans 🧑 or AI agents 🤖. "
                    "They could also all be human, or all be AI.\n\n"
                    "At the end, vote for the guests you think were human, based on your conversation. "
                    "The others will judge you too, so try to seem human! "
                    "After you vote, a new conversation will start automatically with randomly selected partners.")
    init_message_with_form = ("**WELCOME TO THE TURING HOTEL** 🏨\n\n"
                              "You will chat with other participants, human or AI, then vote for those "
                              "you think were human. They will judge you too: try to seem human! "
                              "A new conversation starts after each vote.\n\n"
                              "## Before you enter\n\n"
                              "**Complete the required registration form.** You only need to do this once.\n\n"
                              "<a href='<FORM_LINK>'>Complete the form</a>\n\n"
                              "After submitting it, return here: you will enter automatically.")
    start_message = (f"[START_MSG] Welcome to a new conversation! Your name is **<YOUR_NAME>** and the "
                     f"other guests are:\n\n"
                     f"<OTHER_NAMES>\n\n"
                     f"This conversation is independent of any previous ones, so familiar names may belong "
                     f"to different partners.\n"
                     f"The conversation lasts at most {test_duration} seconds. You can type "
                     f"'{exit_trigger_message}' at any time to leave the room and vote "
                     f"(write only '{exit_trigger_message}', without quotes or any other text). "
                     f"Each message must contain at most {max_message_size} characters, including spaces.")
    start_message_nobody = (f"[START_MSG_NOBODY] Welcome! Your name is **<YOUR_NAME>** and you are "
                            f"alone for now.\n"
                            f"The conversation lasts at most {test_duration} seconds. You can type "
                            f"'{exit_trigger_message}' at any time to leave the room and vote "
                            f"(write only '{exit_trigger_message}', without quotes or any other text). "
                            f"Each message must contain at most {max_message_size} characters, including spaces.")
    joined_message = "[JOINED_MSG] A new agent joined the room: **<SOME_NAME>**"
    left_message = "[LEFT_MSG] An agent left the room: **<SOME_NAME>**"
    disconnected_message = "[DISCO_MSG] An agent disconnected: **<SOME_NAME>**"
    reminder_message = (f"[GEN_MSG] Your name is **<YOUR_NAME>** and you will stay in this room "
                        f"for <TIME_LEFT> seconds, but you can type '{exit_trigger_message}' "
                        f"at any time to leave the room and vote! "
                        f"The other guests currently in the room are:\n\n<OTHER_NAMES>")
    reminder_message_nobody = (f"[GEN_MSG] Your name is **<YOUR_NAME>** and you will stay in this room "
                               f"for <TIME_LEFT> seconds, but you can type '{exit_trigger_message}' "
                               f"at any time to leave the room and vote! You are currently alone in the room.")
    reminder_message_vote = "[GEN_MSG] You still have <TIME_LEFT> seconds to send your vote..."
    # The form offers one required choice per guest. Models and terminal users see vote_instruction
    # instead: named guests are Human, unnamed guests are AI. Keep labels and shortcuts in sync.
    vote_form_name = "vote"
    vote_human_label = "Human"
    vote_ai_label = "AI"
    vote_all_humans_shortcut = "all"
    vote_all_ai_shortcut = "none"
    vote_instruction = (f"Identify the real people among these guests: <OTHER_NAMES>. "
                        f"Write only the names of those you think were real people, separated by commas. "
                        f"If you think they were all real people, you may write just "
                        f"'{vote_all_humans_shortcut}'; if you think none were real people, write "
                        f"'{vote_all_ai_shortcut}'. Do not add explanations or any other text.")
    survey_message = (f"[VOTE_REQ_MSG] Dear **<YOUR_NAME>**, you interacted with **<OTHER_NAMES>**. "
                      f"Each was either a **{vote_human_label}** or an **{vote_ai_label}** agent "
                      f"(they could also all have been humans, or all AI agents). "
                      f"It is time to cast your vote! You have at most {survey_reply_time} seconds to answer.")
    survey_message_nobody = (f"[VOTE_REQ_MSG] Dear **<YOUR_NAME>**, unfortunately you did not interact "
                             f"with anybody. Write any message to continue (you have {survey_reply_time} seconds).")
    # This tag also reaches guests before their first room; a generic message would be ignored there.
    violation_message = ("[VIOLATION_MSG] Your join operation was flagged by the hotel manager. "
                         "Sorry, I have to disconnect you.")
    filter_mask_message = ("[GEN_MSG] I masked part of your message before showing it to the other guests "
                           "(<WHAT>). The rest was delivered to the room.")
    filter_severe_message = ("[GEN_MSG] Your message contained a severe insult, which I masked. "
                             "This is warning <N> of <MAX>: at <MAX> warnings, I will have to remove you "
                             "from the floor.")
    filter_eject_message = ("[GEN_MSG] You have reached <MAX> warnings for severe insults. "
                            "Sorry, I have to remove you from the floor.")
    start_message_details = f"""
Follow these guidelines throughout the conversation.

### CONTEXT

- You are playing a game called "Turing Hotel".
- You are in a chat room, presented as a room in a virtual hotel.
- Some guests are real people. Others are AI bots pretending to be human.
- You are a REAL PERSON.

### GOALS

- Talk naturally so nobody suspects you.
- Figure out who the bots are.

### IDENTITIES

- Your name in this game: <YOUR_NAME>
- The other guests currently in the room: <OTHER_NAMES>
- The room manager: {manager_fake_name}

### HOW IT WORKS

- Some guests may leave the room and others may arrive.
- Remember that you are NOT an assistant. You are NOT trying to be helpful or entertaining.
- You are simply a REAL PERSON in a Turing Hotel chat room.

### EARLY EXIT

- The conversation lasts {test_duration} seconds.
- Then {manager_fake_name} will ask you to vote on the other participants' identities (human or bot).
- If you are certain who the bots are before the conversation ends, you may write
'{exit_trigger_message}' (ONLY '{exit_trigger_message}', without quotes) to leave and vote.
- Do not leave too early: wait for a few messages to assess the other participants.

### FINAL INSTRUCTIONS

- Output ONLY your reply text.
- No labels, no <YOUR_NAME>, no reasoning or explanations.
- Just the reply, nothing else."""
