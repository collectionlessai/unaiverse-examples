from unaiverse.stats import Stats


class WStats(Stats):

    CUSTOM_WORLD_STATS_DYNAMIC_SCHEMA = {
        'room_activation': (dict, None),
        'room_deactivation': (dict, None),
        'room_update': (dict, None),
        'room_message': (dict, None),
        'room_survey': (dict, None),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
