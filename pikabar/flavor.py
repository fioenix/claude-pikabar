"""Pokemon-style flavor text pools and easter eggs.

Voice: Pokemon game narrator, third-person present tense.
Max 28 chars per message to fit the info panel layout.

8 reaction pools + session greetings + critical drama + easter eggs.
"""

import random
from datetime import datetime

# ============================================================
# Reaction-specific flavor text pools (8 per reaction)
# ============================================================

FLAVOR = {
    "idle": [
        "What will {SPECIES} do?",
        "{SPECIES} is waiting...",
        "Ready for battle.",
        "Standing by...",
        "{SPECIES} is alert.",
        "Awaiting orders...",
        "The field is quiet.",
        "{SPECIES} looks around.",
    ],
    "thinking": [
        "{SPECIES} used FOCUS.",
        "{SPECIES} is thinking...",
        "{SPECIES} used DETECT!",
        "Analyzing the field...",
        "A careful approach...",
        "{SPECIES} is strategizing.",
        "Weighing the options...",
        "Deep in thought...",
    ],
    "staging": [
        "{SPECIES} is on alert!",
        "Something's happening...",
        "{SPECIES} senses change!",
        "The field is shifting.",
        "{SPECIES} used AGILITY!",
        "Changes detected!",
        "Activity in the area...",
        "{SPECIES} perked up!",
    ],
    "committed": [
        "{SPECIES} gained EXP!",
        "{SPECIES} leveled up!",
        "Commit captured!",
        "{SPECIES} is pleased!",
        "A wild commit appeared!",
        "Saved the game!",
        "{SPECIES} used CELEBRATE!",
        "Victory fanfare!",
    ],
    "recovered": [
        "HP was restored!",
        "Energy recovered!",
        "Rate limit reset!",
        "Back to full power!",
        "{SPECIES} recovered fully.",
        "Moves fully recharged!",
        "Feeling refreshed!",
        "{SPECIES} is revitalized!",
    ],
    "compacted": [
        "{SPECIES} woke up!",
        "...Where am I?",
        "Memory was cleared!",
        "Hm? What happened?",
        "{SPECIES} is confused!",
        "Context was compacted.",
        "{SPECIES} used REST!",
        "Recovering memories...",
    ],
    "hit": [
        "It's super effective!",
        "{SPECIES} took damage!",
        "{SPECIES} flinched!",
        "A heavy blow!",
        "Rate limit pressure!",
        "{SPECIES} is struggling.",
        "That really hurt...",
        "HP dropping fast!",
    ],
    "faint": [
        "{SPECIES} can't move!",
        "It's fully paralyzed!",
        "Out of PP entirely.",
        "A forced retreat...",
        "Waiting to recover...",
        "{SPECIES} was recalled.",
        "The trainer waits...",
        "{SPECIES} needs time.",
    ],
}

# ============================================================
# HP threshold messages (trigger once per crossing)
# ============================================================

HP_THRESHOLD = {
    50: [
        "Moves are running low...",
        "Conserve your PP.",
        "{SPECIES} is slowing down.",
    ],
    25: [
        "Not many moves remain.",
        "{SPECIES} is struggling.",
        "PP dangerously low!",
    ],
    10: [
        "Almost out of moves!",
        "One last stand...",
        "{SPECIES} can barely move.",
    ],
    0: [
        "{SPECIES} can't move!",
        "Out of PP entirely.",
        "Paralysis took hold.",
    ],
    -1: [  # HP restored (special key)
        "Moves fully recharged!",
        "{SPECIES} recovered fully.",
        "Back to full power!",
    ],
}

# ============================================================
# Easter eggs
# ============================================================

DATE_EGGS = {
    (2, 27): "Happy Pokemon Day!",
    (3, 14): "{SPECIES} used PI ATTACK!",
    (4, 1):  "DITTO used TRANSFORM!",
    (5, 4):  "Use the FORCE, Pika!",
    (10, 31): "BOO! GENGAR appeared!",
    (12, 25): "DELIBIRD used PRESENT!",
    (1, 1):   "Happy New Year! Lv UP!",
}

COST_MILESTONES = {
    1:   "{SPECIES} earned 100P!",
    5:   "That's 500P spent!",
    150: "Evolved into PIKACHU!",
    300: "Evolved into RAICHU!",
    25:  "PROF OAK: Impressive!",
    50:  "Elite Four material!",
    100: "{SPECIES} is CHAMPION!",
}

RARE_RANDOM = [
    "A shiny {SPECIES} appeared!",
    "Wild MISSINGNO. appeared!",
    "{SPECIES} learned FLY!",
    "Found a RARE CANDY!",
    "{SPECIES} used VOLT TACKLE!",
    "A wild MEW appeared!",
    "Master Ball acquired!",
    "{SPECIES} wants to learn...",
    "Old Man glitch activated!",
    "Pika Pika!",
]

# Context-specific number gags
NUMBER_EGGS = {
    42: "The answer to everything.",
    69: "Nice.",
}

# ============================================================
# Evolution flavor (Feature 6)
# ============================================================

EVOLUTION_FLAVOR = [
    "What? {SPECIES} evolved!",
    "{SPECIES} grew to Lv.{N}!",
    "Wow! {SPECIES} evolved!",
    "Evolution complete!",
]


def substitute_species(text, species_name="Pikachu"):
    """Replace {SPECIES} placeholder with actual Pokemon name.

    Falls back gracefully if placeholder missing or already substituted.
    """
    if not species_name:
        species_name = "Pikachu"
    result = text.replace("{SPECIES}", species_name)
    # Safety: if still has placeholder variants, clean up
    result = result.replace("{POKEMON}", species_name)
    return result


# ============================================================
# Session greetings (first call, no previous state)
# ============================================================

def get_session_greeting(pokemon_name="Pikachu"):
    """Return a greeting for the first statusline call of a session."""
    now = datetime.now()
    day = now.weekday()
    if day in SESSION_DAY_GREETINGS and random.random() < 0.5:
        text = SESSION_DAY_GREETINGS[day]
    else:
        text = random.choice(SESSION_GREETINGS)
    return substitute_species(text, pokemon_name)

SESSION_GREETINGS = [
    "{SPECIES}, I choose you!",
    "A wild SESSION appeared!",
    "Trainer entered the arena!",
    "Let the battle begin!",
    "{SPECIES} is ready to go!",
    "Time to code!",
    "A new adventure starts!",
    "{SPECIES} joined the party!",
]

SESSION_DAY_GREETINGS = {
    0: "Monday. Battle stations!",   # Monday
    4: "{SPECIES} used FRIDAY!",       # Friday
    5: "Weekend coding? Bold.",      # Saturday
    6: "Sunday session? Respect.",   # Sunday
}

# ============================================================
# Critical HP drama (HP < 10%)
# ============================================================

CRITICAL_FLAVOR = [
    "It's do or die!",
    "{SPECIES} can barely stand!",
    "One last chance...",
    "Critical HP! Danger!",
    "{SPECIES} is struggling!",
    "Almost out of moves!",
    "{SPECIES} used ENDURE!",
    "Hanging by a thread!",
]


def get_critical_flavor(pokemon_name="Pikachu"):
    """Return dramatic flavor text for critical HP (<10%)."""
    text = random.choice(CRITICAL_FLAVOR)
    return substitute_species(text, pokemon_name)


# ============================================================
# Agent Teams flavor (agent mode)
# ============================================================

AGENT_FLAVOR = [
    "AGENT deployed!",
    "Running recon...",
    "Awaiting orders...",
    "On mission.",
    "Syncing with team...",
    "Team formation!",
    "Specialist active.",
    "Agent standing by.",
]


def get_agent_flavor(agent_name=""):
    """Return flavor text for agent mode. Uses agent name if short enough."""
    if agent_name and len(agent_name) <= 10:
        options = [
            f"{agent_name.upper()} deployed!",
            f"{agent_name.upper()} on mission.",
            f"Go, {agent_name.upper()}!",
        ]
        return random.choice(options + AGENT_FLAVOR)
    return random.choice(AGENT_FLAVOR)


def get_flavor_text(state, hp_pct=None, cost_usd=0.0, duration_min=0,
                    tick=0, chance=0.08, pokemon_name="Pikachu"):
    """Get flavor text for the current reaction state.

    Priority order:
    1. Date-based easter eggs (always fire)
    2. Cost milestones (fire once — caller tracks)
    3. Rare random (0.5% chance)
    4. State flavor (8% chance by default)
    5. Empty string (most of the time)

    Returns:
        Tuple of (text, is_special) where is_special=True for eggs/milestones.
    """
    now = datetime.now()

    # 1. Date-based (check once per session, not per tick)
    if tick == 0:
        key = (now.month, now.day)
        if key in DATE_EGGS:
            return substitute_species(DATE_EGGS[key], pokemon_name), True

    # 2. Rare random (0.5%)
    if random.random() < 0.005:
        return substitute_species(random.choice(RARE_RANDOM), pokemon_name), True

    # 3. Number eggs (exact HP match)
    if hp_pct is not None and hp_pct in NUMBER_EGGS:
        return NUMBER_EGGS[hp_pct], True

    # 4. Duration milestones
    if duration_min == 60 and tick < 3:
        return "Evolved into RAICHU!", True

    # 5. State flavor (default chance)
    if random.random() < chance and state in FLAVOR:
        return substitute_species(random.choice(FLAVOR[state]), pokemon_name), False

    return "", False


def get_evolution_flavor(pokemon_name="Pikachu", level="?"):
    """Return flavor text for evolution event."""
    text = random.choice(EVOLUTION_FLAVOR)
    text = text.replace("{N}", str(level))
    return substitute_species(text, pokemon_name)
