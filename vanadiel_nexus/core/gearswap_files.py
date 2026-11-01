"""Where GearSwap finds a job file and its includes, in GearSwap's own order. Qt-free.

Mirrors Windower4/addons/GearSwap: job file names from refresh.lua:98-105, search directories and per-file
order from refresh.lua:700-729 (pathsearch), include names from user_functions.lua:300-333.
"""
import os
import re
from dataclasses import dataclass, field

# res/jobs.lua `en` per short name. GearSwap builds file names from these (refresh.lua:100-103).
JOB_LONG = {
    'WAR': 'Warrior', 'MNK': 'Monk', 'WHM': 'White Mage', 'BLM': 'Black Mage', 'RDM': 'Red Mage', 'THF': 'Thief',
    'PLD': 'Paladin', 'DRK': 'Dark Knight', 'BST': 'Beastmaster', 'BRD': 'Bard', 'RNG': 'Ranger',
    'SAM': 'Samurai', 'NIN': 'Ninja', 'DRG': 'Dragoon', 'SMN': 'Summoner', 'BLU': 'Blue Mage',
    'COR': 'Corsair', 'PUP': 'Puppetmaster', 'DNC': 'Dancer', 'SCH': 'Scholar', 'GEO': 'Geomancer',
    'RUN': 'Rune Fencer',
}
_CHARACTER_FILE_RE = re.compile(r'^([A-Za-z]{3,15})[_-](.+)\.lua$', re.I)
_CHARACTER_NAME_RE = re.compile(r'^[A-Za-z]{3,15}$')


@dataclass
class JobSearch:
    path: str | None
    shared: bool = False                  # <Char>.lua, <JOB>.lua, <LongJob>.lua or default.lua
    searched: list[str] = field(default_factory=list)


def _appdata(appdata):
    return os.environ.get('APPDATA', '') if appdata is None else appdata


def gearswap_dir(windower_dir: str) -> str:
    return os.path.join(os.path.normpath(windower_dir or '.'), 'addons', 'GearSwap')


def search_dirs(windower_dir: str, character: str, appdata: str = None) -> list[str]:
    """The 9 base directories GearSwap searches, in order (refresh.lua:700-710)."""
    gs = gearswap_dir(windower_dir)
    data = os.path.join(gs, 'data')
    app = os.path.join(_appdata(appdata), 'Windower', 'GearSwap')
    return [os.path.join(gs, 'libs-dev'), os.path.join(gs, 'libs'), os.path.join(data, character), os.path.join(data, 'common'),
            data, os.path.join(app, character), os.path.join(app, 'common'), app,
            os.path.join(os.path.normpath(windower_dir or '.'), 'addons', 'libs')]


def candidates(windower_dir: str, character: str, names: list[str], include_path: str = '',
               appdata: str = None, existing_only: bool = True) -> list[str]:
    """Full candidate paths in GearSwap's exact order: for each base directory (that exists), for each name,
    `<dir>/<include_path>/<name>` when an include path is set, then `<dir>/<name>`."""
    result = []
    for base in search_dirs(windower_dir, character, appdata):
        if existing_only and not os.path.isdir(base):
            continue
        for name in names:
            if not name:
                continue
            if include_path:
                result.append(os.path.join(base, include_path, name))
            result.append(os.path.join(base, name))
    return result


def job_file_names(character: str, job_short: str, job_long: str) -> list[str]:
    """The 8 job file names, in GearSwap's order (refresh.lua:100-103)."""
    return [f'{character}_{job_short}.lua', f'{character}-{job_short}.lua', f'{character}_{job_long}.lua',
            f'{character}-{job_long}.lua', f'{character}.lua', f'{job_short}.lua', f'{job_long}.lua', 'default.lua']


def find_job_file(windower_dir: str, character: str, job: str, appdata: str = None) -> JobSearch:
    """The file GearSwap would load for this character's job. `searched` lists every candidate path."""
    job = (job or '').upper()
    names = job_file_names(character, job, JOB_LONG.get(job, job))
    searched = candidates(windower_dir, character, names, appdata=appdata, existing_only=False)
    for path in searched:  # a file can't exist in a folder that doesn't, so this is GearSwap's order
        if os.path.isfile(path):
            return JobSearch(path, os.path.basename(path).casefold() in {n.casefold() for n in names[4:]}, searched)
    return JobSearch(None, False, searched)


def include_file_name(name: str) -> str:
    """include('Mote-Include') looks for 'mote-include.lua' (user_functions.lua:305-314)."""
    name = name.lower()
    return name if name.endswith('.lua') else name + '.lua'


def find_first(windower_dir: str, character: str, names: list[str], include_path: str = '',
               appdata: str = None) -> tuple[str | None, list[str]]:
    """GearSwap's pathsearch: (first existing candidate or None, candidates checked before it). The earlier
    candidates, including those in folders that don't exist yet, must stay absent for a cached read to stay
    valid."""
    earlier = []
    for path in candidates(windower_dir, character, names, include_path, appdata, existing_only=False):
        if os.path.isfile(path):
            return path, earlier
        earlier.append(path)
    return None, earlier


def resolve_include(name: str, windower_dir: str, character: str, include_path: str = '',
                    appdata: str = None) -> tuple[str | None, list[str]]:
    """Where include(name) finds its file, and the candidates checked before it (see find_first)."""
    return find_first(windower_dir, character, [include_file_name(name)], include_path, appdata)


def allowed_roots(windower_dir: str, appdata: str = None) -> list[str]:
    """The only folders the sandbox may read: the Windower folder and %APPDATA%/Windower/GearSwap."""
    roots = [os.path.realpath(windower_dir or '.')]
    if _appdata(appdata):
        roots.append(os.path.realpath(os.path.join(_appdata(appdata), 'Windower', 'GearSwap')))
    return roots


def inside_roots(path: str, roots: list[str]) -> bool:
    real = os.path.normcase(os.path.realpath(path))
    for root in roots:
        root = os.path.normcase(root)
        if real == root or real.startswith(root.rstrip('\\/') + os.sep):
            return True
    return False


def _job_part(text: str) -> bool:
    folded = text.casefold()
    return any(folded in (short.casefold(), long.casefold()) for short, long in JOB_LONG.items())


def characters_with_files(windower_dir: str) -> set[str]:
    """Character names from data/<Name>_<JOB>.lua, data/<Name>-<JOB>.lua (short or long job) and
    data/<Name>/ folders that hold a job file."""
    data = os.path.join(gearswap_dir(windower_dir), 'data')
    found = set()
    try:
        entries = list(os.scandir(data))
    except OSError:
        return found
    for entry in entries:
        if entry.is_file():
            match = _CHARACTER_FILE_RE.match(entry.name)
            if match and _job_part(match[2]):
                found.add(match[1])
        elif entry.is_dir() and _CHARACTER_NAME_RE.match(entry.name) and entry.name.casefold() != 'common':
            try:
                files = [f.name for f in os.scandir(entry.path) if f.is_file()]
            except OSError:
                continue
            for name in files:
                match = _CHARACTER_FILE_RE.match(name)
                if (name.lower().endswith('.lua') and _job_part(name[:-4])) or (match and _job_part(match[2])):
                    found.add(entry.name)
                    break
    return found
