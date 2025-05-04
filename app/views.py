# Monkey patch
import scipy.signal.windows
import scipy.signal
scipy.signal.hann = scipy.signal.windows.hann

import os
import csv
import librosa
import zipfile
import tempfile
import numpy as np
import re
from collections import defaultdict
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status as http_status
import logging
from io import BytesIO
from pymusickit.key_finder import KeyFinder
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def analyze_music_file(file_path):
    try:
        y, sr = librosa.load(file_path, sr=None, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        key = KeyFinder(file_path).print_key()
        return {'bpm': round(tempo, 1), 'key': key}
    except Exception as e:
        logger.warning(f"Analysis failed for {file_path}: {e}")
        return None

def clean_name(name):
    name = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r'[^\w\s\-]', '', name).strip().replace(' ', '_')

def beatmatch_audio(input_path, original_bpm, target_bpm):
    try:
        audio = AudioSegment.from_file(input_path)
        speed_change = target_bpm / original_bpm
        new_duration = int(len(audio) / speed_change)
        adjusted = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * speed_change)}).set_frame_rate(audio.frame_rate)
        print(f"Beatmatched {input_path} from {original_bpm} to {target_bpm} BPM")
        return adjusted
    except Exception as e: 
        logger.warning(f"Beatmatching failed for {input_path}: {e}")
        return None

def beatmatch_songs(songs):
    if not songs:
        return []
    bpms = [s['bpm'] for s in songs]
    target_bpm = max(set(bpms), key=bpms.count)
    for s in songs:
        s['target_bpm'] = target_bpm
    return songs

def create_zip_response(files):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            if os.path.exists(f['source_path']):
                zipf.write(f['source_path'], f['zip_path'])
            else:
                logger.warning(f"File missing during zip: {f['source_path']}")
    resp = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    resp['Content-Disposition'] = 'attachment; filename="mashups.zip"'
    return resp

@api_view(['POST'])
def generate_mashups(request):
    logger.info("generate_mashups called")
    try:
        files = request.FILES.getlist('files')
        if not files:
            return JsonResponse({'error': 'No files uploaded'}, status=400)

        output_format = request.POST.get('output_format', 'filesystem')

        temp_dir = tempfile.mkdtemp()
        for f in files:
            save_path = os.path.join(temp_dir, f.name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb+') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)

        song_groups = defaultdict(list)
        for root, _, fs in os.walk(temp_dir):
            for f in fs:
                if f.lower().endswith('.mp3'):
                    prefix = ' - '.join(f.split(' - ')[:2])
                    # print(f"Prefix: {prefix}, File: {f}")
                    song_groups[prefix].append(os.path.join(root, f))

        songs = []
        for raw_name, filepaths in song_groups.items():
            components = {}
            for path in filepaths:
                fname = os.path.basename(path).lower()
                if 'vocal' in fname and 'instrumental' in fname:
                    components['full'] = path
                    # print(f"Added full component: {path}")
                elif 'vocal' in fname:
                    components['vocals'] = path
                    # print(f"Added vocal component: {path}")
                elif 'instrumental' in fname:
                    components['instrumental'] = path
                    # print(f"Added instrumental component: {path}")
                else:
                    # print(f"Unknown component in {fname}, skipping")
                    pass

            if 'full' not in components:
                continue

            analysis = analyze_music_file(components['full'])
            
            if analysis:
                songs.append({
                    'name': raw_name.split(' - ')[-1] if ' - ' in raw_name else raw_name,
                    'components': components,
                    'bpm': analysis['bpm'],
                    'key': analysis['key'],
                    'tempos': [analysis['bpm'], analysis['bpm']/2] if analysis['bpm'] > 144 else [analysis['bpm']],
                    'original_bpm': analysis['bpm'], 
                    'artist': raw_name.split(' - ')[0] if ' - ' in raw_name else 'Unknown'
                })

        if not songs:
            return JsonResponse({'error': 'No valid songs found'}, status=400)

        key_groups = defaultdict(list)

        for song in songs:
            key_groups[song['key']].append(song)

        beatmatched_groups = {k: beatmatch_songs(g) for k, g in key_groups.items()}

        output_data = []
        files_to_zip = []

        for key, group in beatmatched_groups.items():
            if len(group) == 1:
                song = group[0]
                solo_folder = f"{song['name']}"
                for comp in ['full', 'vocals', 'instrumental']:
                    if comp in song['components']:
                        files_to_zip.append({
                            'source_path': song['components'][comp],
                            'zip_path': f"{solo_folder}/{song['name']}^{song['artist']}^{song['bpm']}^{song['key']}^Song A^{comp.capitalize()}.mp3"
                        })
                output_data.append({
                    'song1': song['name'],
                    'song1_bpm': song['bpm'],
                    'song1_artist': song['artist'],
                    'song2': None,
                    'song2_bpm': None,
                    'song2_artist': None,
                    'target_bpm': None,
                    'original_bpm': song['original_bpm'],
                    'key': key,
                    'folder': solo_folder
                })
            else:
                for i, s1 in enumerate(group):
                    for j, s2 in enumerate(group):
                        if i == j:
                            continue
                        # Mashup Folder should be song1 + song2 (No artist name)
                        mashup_folder = f"{s1['name']} + {s2['name']}"
                        for comp in ['full', 'vocals', 'instrumental']:
                            # ✅ Always include Song A components (copy only)
                            if comp in s1['components']:
                                files_to_zip.append({
                                    'source_path': s1['components'][comp],
                                    'zip_path': f"{mashup_folder}/{s1['name']}^{s1['artist']}^{s1['bpm']}^{s1['key']}^Song A^{comp.capitalize()}.mp3"
                                })
                                # print(f"Added {s1['components'][comp]} to zip as {s1['name']}^Song A^{comp.capitalize()}.mp3")

                            # ✅ Attempt to beatmatch Song B component
                            new_bpm = s1['original_bpm']
                            if comp in s2['components']:
                                if abs(s2['bpm'] - s1['original_bpm']) <= 22:
                                    adjusted = beatmatch_audio(
                                        s2['components'][comp],
                                        original_bpm=s2['bpm'],
                                        target_bpm=s1['original_bpm']
                                    )
                                elif abs(s2['bpm'] - s1['original_bpm']) > 42:
                                    print(f"Skipping beatmatching for {s2['components'][comp]} due to BPM difference")
                                    adjusted = None
                                else:
                                    #Average of bpms
                                    new_bpm = (s1['original_bpm'] + s2['bpm']) / 2
                                    adjusted = beatmatch_audio(
                                        s2['components'][comp],
                                        original_bpm=s2['bpm'],
                                        target_bpm=new_bpm
                                    )
                                    
                                if adjusted:
                                    pair_id = f"{s1['name']}_TO_{s2['name']}_{comp}"
                                    temp_out = os.path.join(tempfile.mkdtemp(), f"adjusted_{pair_id}.mp3")
                                    adjusted.export(temp_out, format="mp3")
                                    source_path = temp_out
                                else:
                                    logger.warning(f"Falling back to original for {s2['components'][comp]}")
                                    source_path = s2['components'][comp]

                                files_to_zip.append({
                                    'source_path': source_path,
                                    'zip_path': f"{mashup_folder}/{s2['name']}^{s2['artist']}^{new_bpm}^{s2['key']}^Song B^{comp.capitalize()}.mp3"
                                })
                                #print(f"Added {s2['components'][comp]} to zip as {s2['name']}^Song B^{comp.capitalize()}.mp3")
                            else:
                                #print(f"Component {comp} not found for {s2['name']} or {s1['name']}")
                                pass

                        output_data.append({
                            'song1': s1['name'],
                            'song1_artist': s1['artist'],
                            'song1_key': s1['key'],
                            'song1_bpm': s1['bpm'],
                            'song2': s2['name'],
                            'song2_artist': s2['artist'],
                            'song2_bpm': s2['bpm'],
                            'target_bpm': s1['target_bpm'],
                            'key': key,
                            'folder': mashup_folder
                        })



        if output_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="mashups.csv"'
            
            # Ensure 'original_bpm' is included in the fieldnames
            fieldnames = list(output_data[0].keys())
            writer = csv.DictWriter(response, fieldnames=fieldnames)
            writer.writeheader()
            for row in output_data:
                filtered_row = {k: row[k] for k in fieldnames if k in row}
                writer.writerow(filtered_row)

            return response
        else:
            return create_zip_response(files_to_zip)

    except Exception as e:
        logger.exception("Processing failed")
        return JsonResponse({'error': 'Internal server error'}, status=500)


