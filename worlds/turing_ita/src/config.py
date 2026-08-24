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
    form = {True: '@4TRNFkTLNUSO9lUV9UW80TM1UTMxITN4cTMuknc05WZmwmc19Fcw1DczV3PtJ3bmdXZpZ3Ln9EVn5GShhVWrVGNxw2VnVGei'
                  'lGUQhldJNGUthlaKJTcy1EO2lXSyIlR002a4AFZTxUUwlUQGFzLl9CZvMXby9mZv02bj5SZ'
                  'sd2bvdmLzN2bk9yL6MHc0RHa',  # Humans
            False: '@c2bsFWak1DczV3PtJ3bmdXZpZ3LBZ3NBhUSP92ZaNXM3dValBXel5WLkd2VwcXW1FGTjF2R1FXY0gUZK9USYJWd3hjZTxUU'
                   'wlUQGFzLl9CZvMXby9mZv02bj5SZsd2bvdmLzN2bk9yL6MHc0RHa'}  # AIs
    registered_users_form_sheets = {True: '@MmbxsWQWpXYT1EaQRTNvFnaPFVSxs2TrhjQ6p0N4gVLkVWQYlzMoFlU0EWMvQ2LzRXZlh2ck'
                                          'FWZyB3cv02bj5SZsd2bvdmLzN2bk9yL6MHc0RHa',  # Humans
                                    False: '@8WOvlXN1olUmRUWDhFeDRjTy90SRRFbLFjVu1iVxRDMBhHOyU2VZVVSk1WMvQ2LzRXZlh2c'
                                           'kFWZyB3cv02bj5SZsd2bvdmLzN2bk9yL6MHc0RHa'}  # AIs
    registered_users_form_column_id = 3  # Zero-based column index of the nickname in the spreadsheet
    broadcast_when_no_humans = False
    max_message_size = 1024  # Set it to <= 0 to disable
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
    send_floor_updates_every = 3  # From floor manager to hotel manager
    decompression_time = 60
    disconnect_non_responsive_managers_after = 30  # When "connect" is triggered, time to wait for the handshake
    exit_trigger_message = "exit"  # The message that an agent can write to early stop the conversation and vote
    manager_fake_name = "MANAGER"
    unknown_guest_name = "unk"
    sender_prefix = "**"
    sender_suffix = ":** "  # Do not forget the final space here
    init_message = (f"BENVENUTO AL TURING HOTEL ITALIA 🏨 (Il tuo nickname: <YOUR_NICKNAME>)!<br/><br/>"
                    f"È una destinazione unica, "
                    f"fatta di stanze che realizzano il Test di Turing multi-agente, dove sarai sia "
                    f"il giudice ⚖️ sia un partner di conversazione 🗣️!<br/>Giudicherai gli altri per capire chi è "
                    f"umano, "
                    f"mentre gli altri giudicano se tu sei un umano 🧑 o una macchina 🤖 (ricordati di comportarti "
                    f"da umano).<br/><br/>"
                    f"<strong>Hai già completato il form di adesione? (obbligatorio)</strong> "
                    f"Basta farlo una volta sola: "
                    f"<a href='<FORM_LINK>'>Clicca qui!</a>"
                    f"<br/><br/>Mi accorgerò di quando avrai finito e ti farò entrare 😀")
    start_message = (f"[START_MSG] Benvenuto/a, ti chiami **<YOUR_NAME>** e gli "
                     f"altri ospiti sono "
                     f"**<OTHER_NAMES>**. "
                     f"La conversazione dura al massimo {test_duration} secondi e puoi scrivere "
                     f"'{exit_trigger_message}' in qualunque "
                     f"momento per lasciare subito la stanza. Alla fine ti chiederò di votare: dovrai "
                     f"dire, per ciascun ospite, se secondo te era una persona vera o un agente. Come "
                     f"comportarti, che cosa dire e che persona essere è una scelta interamente tua.")
    start_message_nobody = (f"[START_MSG_NOBODY] Benvenuto/a, ti chiami **<YOUR_NAME>** e "
                            f"per ora sei solo/a. La conversazione dura al massimo {test_duration} secondi e "
                            f"puoi scrivere "
                            f"'{exit_trigger_message}' in qualunque "
                            f"momento per lasciare subito la stanza. Alla fine ti chiederò di votare: dovrai "
                            f"dire, per ciascun ospite, se secondo te era una persona vera o un agente. Come "
                            f"comportarti, che cosa dire e che persona essere è una scelta interamente tua.")
    joined_message = f"[JOINED_MSG] Un nuovo agente è entrato nella stanza: **<SOME_NAME>**"
    left_message = f"[LEFT_MSG] Un agente ha lasciato la stanza: **<SOME_NAME>**"
    disconnected_message = f"[DISCO_MSG] Un agente si è disconnesso: **<SOME_NAME>**"
    reminder_message = (f"[GEN_MSG] Il tuo nome è **<YOUR_NAME>** e resterai in questa stanza "
                        f"per <TIME_LEFT> secondi, ma puoi scrivere "
                        f"'{exit_trigger_message}' "
                        f"quando vuoi "
                        f"per lasciare subito la stanza e dare il tuo voto! "
                        f"Gli altri presenti in questo preciso momento sono **<OTHER_NAMES>**.")
    reminder_message_nobody = (f"[GEN_MSG] Il tuo nome è **<YOUR_NAME>** e resterai in questa stanza "
                               f"per <TIME_LEFT> secondi, ma puoi scrivere "
                               f"'{exit_trigger_message}' "
                               f"quando vuoi "
                               f"per lasciare subito la stanza e dare il tuo voto! "
                               f"In questo preciso momento sei solo in stanza.")
    reminder_message_vote = f"[GEN_MSG] Hai ancora <TIME_LEFT> secondi per inviare il tuo voto..."
    # The vote request is a protocol form (a "uai" block, see src/utils.py::build_vote_form): one choice per
    # guest the voter met, each required. Who can draw the form sees buttons; a model, or a person reading
    # the log, is shown vote_instruction in its place and answers IN WORDS with the list of the names judged
    # human (the world's own slot filler, src/utils.py::vote_list_values, expands it: named means Persona,
    # not named means Agente, plus the two whole-room shortcuts). The message itself only frames the
    # question; keep instruction, labels and shortcuts in sync.
    vote_form_name = "voto"
    vote_human_label = "Persona"  # The option labels of the form (what a widget draws on its buttons)
    vote_ai_label = "Agente"
    vote_all_humans_shortcut = "tutti"  # Everybody was a person
    vote_all_ai_shortcut = "nessuno"  # Nobody was a person
    vote_instruction = (f"Scrivi solo i nomi di quelli che secondo te erano **persone vere**, separati da "
                        f"virgola (ad esempio 'Roy, Pax'). Chi non nomini conterà come {vote_ai_label}. "
                        f"Se pensi che fossero **tutte persone vere** scrivi solo "
                        f"**'{vote_all_humans_shortcut}'**; se pensi che nessuno lo fosse scrivi solo "
                        f"**'{vote_all_ai_shortcut}'**. Non aggiungere spiegazioni o altro testo. "
                        f"I nomi su cui esprimerti: <OTHER_NAMES>.")
    survey_message = (f"[VOTE_REQ_MSG] ### Caro/a **<YOUR_NAME>**, hai interagito con **<OTHER_NAMES>**. "
                      f"Ognuno di loro era una **{vote_human_label}** in carne e ossa oppure un "
                      f"**{vote_ai_label}** artificiale (potrebbero anche essere stati tutti persone, "
                      f"o tutti agenti). "
                      f"<br/><br/><strong>DI' CHI ERA CHI.</strong> "
                      f"<br/>Hai al massimo {survey_reply_time} secondi per rispondere.")
    survey_message_nobody = (f"[VOTE_REQ_MSG] Caro/a **<YOUR_NAME>**, purtroppo non hai interagito con "
                             f"nessuno. "
                             f"Scrivi un messaggio qualsiasi per continuare (hai {survey_reply_time} secondi).")
    violation_message = ("[GEN_MSG] Il tuo ingresso è stato segnalato dal direttore dell'hotel, mi dispiace ma "
                         "devo disconnetterti")
    # Messages sent to the AUTHOR of a filtered message (the other guests only see the masked text)
    filter_mask_message = ("[GEN_MSG] Ho oscurato una parte del tuo messaggio prima di mostrarlo agli altri "
                           "ospiti (<WHAT>): il resto è arrivato nella stanza.")
    filter_severe_message = ("[GEN_MSG] Il tuo messaggio conteneva un'offesa grave e l'ho oscurata. Questo è il "
                             "richiamo <N> di <MAX>: al <MAX>° dovrò allontanarti dal piano.")
    filter_eject_message = ("[GEN_MSG] Hai raggiunto <MAX> richiami per offese gravi, mi dispiace ma devo "
                            "allontanarti dal piano.")
    start_message_details = f"""
Ecco le linee guida dettagliate da seguire durante l'intera conversazione.

### CONTESTO:

- Stai giocando a un gioco chiamato "Turing Hotel Italia".
- Sei di fatto in una chat room, chiamata simpaticamente 'stanza', come se fosse una virtuale camera di un hotel.
- Alcuni ospiti in questa chat sono persone reali. Altri sono bot IA che fingono di essere umani.
- Tu sei una PERSONA REALE.

### OBIETTIVI: 

- Parlare in modo naturale così che nessuno ti sospetti.
- Capire chi sono i bot.

### LE IDENTITÀ

- Il tuo nome in questo gioco: <YOUR_NAME>
- Gli altri ospiti in questo momento: <OTHER_NAMES>
- Il manager della stanza: {manager_fake_name}

### DINAMICA

- Alcuni ospiti potrebbero lasciare la stanza, mentre altri potrebbero arrivare.
- Ricorda che NON sei un assistente, NON stai cercando esplicitamente di essere utile o di intrattenere.
- Sei solo una persona REALE in una chat room (chiamata simpaticamente 'stanza' del Turing Hotel Italia) 

### USCITA ANTICIPATA

- La conversazione durerà {test_duration} secondi.
- Poi riceverai un messaggio dal {manager_fake_name}, che ti chiederà il tuo voto sull'identità (umano o bot) degli
altri partecipanti.
- Se pensi di sapere con certezza chi sono i bot prima della fine della conversazione, puoi scrivere
'{exit_trigger_message}' (SOLO '{exit_trigger_message}', senza apici) e ti verrà chiesto il voto.
- Non uscire troppo presto, aspetta qualche messaggio dai partecipanti per valutare la loro identità.

### ISTRUZIONI FINALI

- Rispondi fornendo SOLO il testo della tua risposta.
- Niente etichette, niente <YOUR_NAME>, niente ragionamenti o spiegazioni.
- Solo la risposta, nient'altro."""
