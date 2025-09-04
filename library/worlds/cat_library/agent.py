from unaiverse.agent import Agent


class CatLibraryRoles:
    # Role bitmasks
    ROLE_TEACHER = 1 << 2
    ROLE_STUDENT = 1 << 3

    # Feasible roles
    ROLE_BITS_TO_STR = {
        # The base roles will be inherited from AgentBasics later
        ROLE_TEACHER: "teacher",
        ROLE_STUDENT: "student",
    }


class WAgent(Agent, CatLibraryRoles):
    # feasible roles
    ROLE_BITS_TO_STR = {**Agent.ROLE_BITS_TO_STR, **CatLibraryRoles.ROLE_BITS_TO_STR}
    ROLE_STR_TO_BITS = {v: k for k, v in ROLE_BITS_TO_STR.items()}
