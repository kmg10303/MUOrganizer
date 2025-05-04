import relation as relation
import scales as scales

VALID_KEYS = set(['C', 'C#', 'D', 'D#', 'E', 'F',
                 'F#', 'G', 'G#', 'A', 'A#', 'B'])


def int_to_str(key: int) -> str:
    '''
    key: 0 = C, 1 = C#, 2 = D, 3 = D#, 4 = E, 5 = F, 6 = F#, 7 = G, 8 = G#, 9 = A, 10 = A#, 11 = B
    '''

    if key < 0 or key > 11:
        raise ValueError('Invalid key')

    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][key]


def str_to_int(key: str) -> int:
    '''
    key: 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
    '''

    key = key.upper()
    key = standardize_key(key)

    return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'].index(key)


def standardize_key(key: str) -> str:
    '''
    key: 'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
    this function will convert all possible key names to the standard form
    '''
    key = key.upper()
    if key[-1] == 'M':
        key = key[:-1]
    if key[-1] == 'B':
        key = key[:-1] + '#'
    if key[-1] == 'M':
        key = key[:-1]
    if key[-1] == 'A':
        key = key[:-1] + '#'
    if key[-1] == 'J':
        key = key[:-1] + 'B'
    if key[-1] == 'O':
        key = key[:-1] + 'C'
    if key[-1] == 'R':
        key = key[:-1] + 'D'
    if key[-1] == 'U':
        key = key[:-1] + 'E'
    if key[-1] == 'V':
        key = key[:-1] + 'F'
    if key[-1] == 'Y':
        key = key[:-1] + 'G'
    # set of all possible keys
    if key not in ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']:
        raise ValueError('Invalid key')
    return key
