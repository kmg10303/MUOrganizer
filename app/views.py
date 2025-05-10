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
import soundfile as sf
import shutil
from django.shortcuts import render

def index(request):
    return render(request, 'index.html')


logger = logging.getLogger(__name__)

def analyze_music_file(file_path):
    try:
        y, sr = librosa.load(file_path, sr=None, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        key = KeyFinder(file_path).print_key()
        return {'bpm': tempo, 'key': key}
    except Exception as e:
        logger.warning(f"Analysis failed for {file_path}: {e}")
        return None

def clean_name(name):
    name = os.path.splitext(os.path.basename(name))[0]
    return re.sub(r'[^\w\s\-]', '', name).strip().replace(' ', '_')

def beatmatch_audio(input_path, original_bpm, target_bpm):
    try:
        rate = target_bpm / original_bpm
        y, sr = librosa.load(input_path, sr=None)
        y_stretched = librosa.effects.time_stretch(y, rate=rate)

        temp_out = tempfile.mktemp(suffix=".mp3")
        sf.write(temp_out, y_stretched, sr)
        
        # Load the created file as AudioSegment
        audio = AudioSegment.from_file(temp_out)
        print(f"Beatmatched {input_path} from {original_bpm} to {target_bpm} BPM")
        return audio
    except Exception as e:
        logger.warning(f"Beatmatching failed: {e}")
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

        csv_data = []
        files_to_zip = []

        for key, group in beatmatched_groups.items():
            for i, s1 in enumerate(group):
                for j, s2 in enumerate(group):
                    if len(group) == 1:
                        song = group[0]
                        solo_folder = f"{song['key']}/{song['name']}"
                        for comp in ['full', 'vocals', 'instrumental']:
                            if comp in song['components']:
                                files_to_zip.append({
                                    'source_path': song['components'][comp],
                                    'zip_path': f"{solo_folder}/{song['name']}^{song['artist']}^{song['bpm']}^{song['key']}^Song A^{comp.capitalize()}.mp3"
                                })
                        csv_data.append({
                            'Song A title': song['name'],
                            'Song A artist': song['artist'],
                            'Song A Key': song['key'],
                            'Song A Tempo': round(song['bpm'],1),
                            'Song B title': '',
                            'Song B artist': '',
                            'Song B Key': '',
                            'Song B Tempo': '',
                            'Song A vocal path': f"{solo_folder}/{song['name']}^{song['artist']}^{round(song['bpm'],1)}^{song['key']}^Song A^Vocals.mp3" if 'vocals' in song['components'] else '',
                            'Song A instrumental path': f"{solo_folder}/{song['name']}^{song['artist']}^{round(song['bpm'],1)}^{song['key']}^Song A^Instrumental.mp3" if 'instrumental' in song['components'] else '',
                            'Song A full path': f"{solo_folder}/{song['name']}^{song['artist']}^{round(song['bpm'],1)}^{song['key']}^Song A^Full.mp3" if 'full' in song['components'] else '',
                            'Song B vocal path': '',
                            'Song B instrumental path': '',
                            'Song B full path': ''
                        })
                    else:   
                        if i == j:
                            continue
                        mashup_folder = f"{s1['key']}/{s1['name']} + {s2['name']}"
                        for comp in ['full', 'vocals', 'instrumental']:
                            if comp in s1['components']:
                                files_to_zip.append({
                                    'source_path': s1['components'][comp],
                                    'zip_path': f"{mashup_folder}/{s1['name']}^{s1['artist']}^{round(s1['bpm'],1)}^{s1['key']}^Song A^{comp.capitalize()}.mp3"
                                })
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
                                    print(f"Average BPM for {s1['name']} and {s2['name']}: {new_bpm}")
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
                                new_bpm = round(new_bpm, 1)
                                files_to_zip.append({
                                    'source_path': source_path,
                                    'zip_path': f"{mashup_folder}/{s2['name']}^{s2['artist']}^{new_bpm}^{s2['key']}^Song B^{comp.capitalize()}.mp3"
                                })
                        zip_folder = f"{s1['key']}/{s1['name']} + {s2['name']}"
                        csv_data.append({
                            'Song A title': s1['name'],
                            'Song A artist': s1['artist'],
                            'Song A Key': s1['key'],
                            'Song A Tempo': round(new_bpm,1),
                            'Song B title': s2['name'],
                            'Song B artist': s2['artist'],
                            'Song B Key': s2['key'],
                            'Song B Tempo': round(new_bpm,1),
                            'Song A vocal path': f"{zip_folder}/{s1['name']}^{s1['artist']}^{new_bpm}^{s1['key']}^Song A^Vocals.mp3" if 'vocals' in s1['components'] else '',
                            'Song A instrumental path': f"{zip_folder}/{s1['name']}^{s1['artist']}^{new_bpm}^{s1['key']}^Song A^Instrumental.mp3" if 'instrumental' in s1['components'] else '',
                            'Song A full path': f"{zip_folder}/{s1['name']}^{s1['artist']}^{new_bpm}^{s1['key']}^Song A^Full.mp3" if 'full' in s1['components'] else '',
                            'Song B vocal path': f"{zip_folder}/{s2['name']}^{s2['artist']}^{new_bpm}^{s2['key']}^Song B^Vocals.mp3" if 'vocals' in s2[ 'components'] else '',
                            'Song B instrumental path': f"{zip_folder}/{s2['name']}^{s2['artist']}^{new_bpm}^{s2['key']}^Song B^Instrumental.mp3" if 'instrumental' in s2['components'] else '',
                            'Song B full path': f"{zip_folder}/{s2['name']}^{s2['artist']}^{new_bpm}^{s2['key']}^Song B^Full.mp3" if 'full' in s2['components'] else ''
                        })
        
        # Write CSV
        csv_path = os.path.join(temp_dir, 'mu_prep_summary.csv')
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'Song A title', 
                'Song A artist', 
                'Song A Key', 
                'Song A Tempo',
                'Song B title', 
                'Song B artist', 
                'Song B Key', 
                'Song B Tempo',
                'Song A vocal path', 'Song A instrumental path', 'Song A full path',
                'Song B vocal path', 'Song B instrumental path', 'Song B full path'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in csv_data:
                # Convert absolute paths to relative if needed
                for key in row:
                    if 'path' in key and row[key]:
                        row[key] = os.path.relpath(row[key], temp_dir)
                writer.writerow(row)
        
        print(f"Metadata summary written to: {csv_path}")
        
        files_to_zip.append({
            'source_path': csv_path,
            'zip_path': 'mu_prep_summary.csv'
        })

        if output_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="mashups.csv"'
            
            # Ensure 'original_bpm' is included in the fieldnames
            fieldnames = list(csv_data[0].keys())
            writer = csv.DictWriter(response, fieldnames=fieldnames)
            writer.writeheader()
            for row in csv_data:
                filtered_row = {k: row[k] for k in fieldnames if k in row}
                writer.writerow(filtered_row)

            return response
        else:
            return create_zip_response(files_to_zip)

    except Exception as e:
        logger.exception("Processing failed")
        return JsonResponse({'error': 'Internal server error'}, status=500)


