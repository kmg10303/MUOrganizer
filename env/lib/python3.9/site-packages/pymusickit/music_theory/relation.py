def relative_minor(major_key: str) -> str:
    """
    Returns the relative minor key for a given major key.

    Parameters:
    key (str): The major key to find the relative minor for.

    Returns:
    str: The relative minor key.
    """

    # Create a dictionary mapping major keys to their relative minor keys
    relative_minor_dict = {'C': 'A', 'G': 'E', 'D': 'B', 'A': 'F#', 'E': 'C#', 'B': 'G#', 'F#': 'D#',
                           'Gb': 'Eb', 'Db': 'Bb', 'Ab': 'F', 'Eb': 'C', 'Bb': 'G', 'F': 'D'}

    # Look up the relative minor key and return it
    return relative_minor_dict[major_key]


def relative_major(minor_key: str) -> str:
    """
    Returns the relative major key for a given minor key.

    Parameters:
    key (str): The minor key to find the relative major for.

    Returns:
    str: The relative major key.
    """

    # Create a dictionary mapping minor keys to their relative major keys
    relative_major_dict = {'A': 'C', 'E': 'G', 'B': 'D', 'F#': 'A', 'C#': 'E', 'G#': 'B', 'D#': 'F#',
                           'F': 'Ab', 'C': 'Eb', 'G': 'Bb', 'D': 'F', 'Bb': 'Db', 'Eb': 'Gb'}

    # Look up the relative major key and return it
    return relative_major_dict[minor_key]
