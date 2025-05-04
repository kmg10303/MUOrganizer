class Scales:

    def major_scale(key: int) -> list:
        '''
        key: 0 = C, 1 = C#, 2 = D, 3 = D#, 4 = E, 5 = F, 6 = F#, 7 = G, 8 = G#, 9 = A, 10 = A#, 11 = B
        '''
        steps = [2, 2, 1, 2, 2, 2, 1]
        notes = [key]
        for i in range(len(steps)):
            note = (notes[i] + steps[i]) % 12
            notes.append(note)
        return notes

    def natural_minor_scale(key: int) -> list:
        '''
        key: 0 = C, 1 = C#, 2 = D, 3 = D#, 4 = E, 5 = F, 6 = F#, 7 = G, 8 = G#, 9 = A, 10 = A#, 11 = B
        '''
        steps = [2, 1, 2, 2, 1, 2, 2]
        notes = [key]
        for i in range(len(steps)):
            note = (notes[i] + steps[i]) % 12
            notes.append(note)
        return notes

    def chromatic_scale(key: int) -> list:
        '''
        key: 0 = C, 1 = C#, 2 = D, 3 = D#, 4 = E, 5 = F, 6 = F#, 7 = G, 8 = G#, 9 = A, 10 = A#, 11 = B
        '''
        notes = [key]
        for i in range(1, 12):
            note = (key + i) % 12
            notes.append(note)
        return notes

    def pentatonic_scale(key: int) -> list:
        '''
        key: 0 = C, 1 = C#, 2 = D, 3 = D#, 4 = E, 5 = F, 6 = F#, 7 = G, 8 = G#, 9 = A, 10 = A#, 11 = B
        '''
        notes = [(key + i*7) % 12 for i in range(5)]
        return notes

    def modal_scale(key: int, mode: int) -> list:
        '''
        key: 0 = C, 1 = C#, 2 = D, 3 = D#, 4 = E, 5 = F, 6 = F#, 7 = G, 8 = G#, 9 = A, 10 = A#, 11 = B
        mode: 0 = Ionian, 1 = Dorian, 2 = Phrygian, 3 = Lydian, 4 = Mixolydian, 5 = Aeolian, 6 = Locrian
        '''
        steps = [2, 2, 1, 2, 2, 1, 2]
        notes = [key]
        for i in range(len(steps)):
            note = (notes[i] + steps[i]) % 12
            notes.append(note)
        notes = notes[mode:] + notes[:mode]
        return notes
