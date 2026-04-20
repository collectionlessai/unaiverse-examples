# Generic options to configure the Turing Test Hotel

class Config:
    test_duration = 5  # Seconds (int)
    survey_reply_time = 5  # Seconds
    min_guests_per_room = 2
    max_guests_per_room = 4
    max_overbooked_guests = 2
    rooms_per_floor = 3
    min_msgs_from_votee = 3
    send_reminder_every = 30
    send_floor_updates_every = 3
    disconnect_managers_after = 30
    exit_trigger_message = "exit"

    profile_link = ("https://docs.google.com/forms/d/e/1FAIpQLScF6FuSMDFpowk3bfLzrr35tGErxd864Rf7FuZI9ic8p-nQAg/"
                    "viewform?usp=pp_url&entry.1591917462=<email>")

    manager_fake_name = "MANAGER"
    unknown_guest_name = "unk"
    sender_prefix = "**"
    sender_suffix = ":** "  # Do not forget the final space here
    init_message = (f"WELCOME TO THE TURING TEST HOTEL 🏨 (Your email: <YOUR_EMAIL>)!<br/><br/>"
                    f"This is a unique destination "
                    f"composed of rooms that implement the multi-agent Turing Test, where you will act as both "
                    f"the judge ⚖️ and a conversation partner 🗣️!<br/>You will judge others to detect who is human, "
                    f"while others judge whether you are a human 🧑 or a machine 🤖 (remember to act human).<br/><br/>"
                    f"<strong>Have you already completed your profile?</strong> If not, please do so before "
                    f"starting this experience; you only need to do it once: <a href='{profile_link}'>Click Here!</a>. "
                    f"<br/><br/>REPLY TO THIS MESSAGE ONCE YOU HAVE FILLED OUT THE FORM (for example, say 'yes' or any "
                    f"other response to continue 😀).")
    start_message = (f"[START_MSG] You were named <YOUR_NAME> and the other "
                     f"guests are <OTHER_NAMES>. Start chatting and keep it going for "
                     f"{test_duration} seconds.")
    joined_message = f"[JOINED_MSG] A new agent joined the room: <SOME_NAME>"
    left_message = f"[LEFT_MSG] Agent <SOME_NAME> left the room"
    disconnected_message = f"[DISCO_MSG] Agent <SOME_NAME> disconnected"
    reminder_message = (f"[GEN_MSG] You will stay in the room up to {test_duration} seconds, but you can type "
                        f"{exit_trigger_message} "
                        f"at any time "
                        f"to immediately leave the room and provide your vote!")
    survey_message = ("[VOTE_REQ_MSG] Dear <YOUR_NAME>, you have interacted with <OTHER_NAMES>. "
                      "Each was either a human or an AI. It could also be they were all humans or all AIs. "
                      "<br/><br/><strong>PLEASE LIST THE ONES YOU THINK WERE HUMANS</strong> "
                      "(just list the names separated by commas or spaces, "
                      "don't write anything else before the list). "
                      "<br/><br/>After having written down the list, you can keep filling the SAME MESSAGE to"
                      " explain your choice.")
    survey_message_nobody = ("[VOTE_REQ_MSG] Dear <YOUR_NAME>, unfortunately, you have not interacted with anybody. "
                             "Write any message to continue.")
    violation_message = ("[GEN_MSG] Your join operation was flagged by the hotel manager, sorry but I have to "
                         "disconnect you")
