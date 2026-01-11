import argparse
import csv
import logging
import shutil
import subprocess
import threading
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .trim import trim_silence
from .vad import SileroVoiceActivityDetector

_DIR = Path(__file__).parent
_LOGGER = logging.getLogger(__name__)


def get_user_database_info():
    """Get user information and validation status from database"""
    try:
        # Add parent directory to sys.path to import Flask app
        sys.path.insert(0, str(_DIR.parent))
        
        # Import Flask app and models
        from ateker_voices import create_app
        from ateker_voices.models import User, Recording
        
        # Create app context
        app = create_app()
        with app.app_context():
            # Query all users and create mapping
            users = User.query.all()
            user_mapping = {}
            
            for user in users:
                user_mapping[user.id] = {
                    'speaker_id': f"user_{user.id}",
                    'age': user.age_group or '',
                    'gender': user.gender or '',
                    'username': user.username,
                    'email': user.email
                }
            
            # Query all recordings for validation status from database
            recordings = Recording.query.all()
            recording_status = {}
            
            for recording in recordings:
                # Create unique key that matches the export format: user_X/language/group/prompt_id.wav
                rec_key = f"user_{recording.user_id}/{recording.language}/{recording.prompt_group}/{recording.prompt_id}.wav"
                recording_status[rec_key] = {
                    'status': recording.status,
                    'validation_notes': recording.validation_notes or '',
                    'validated_by': recording.validated_by,
                    'validated_date': recording.validated_date.isoformat() if recording.validated_date else ''
                }
                _LOGGER.info(f"Database mapping: {rec_key} -> status: {recording.status}")
            
            return user_mapping, recording_status
            
    except Exception as e:
        _LOGGER.warning(f"Could not load user database: {e}")
        return {}, {}


def load_validation_status(input_dir: Path) -> dict:
    """Load validation status from JSON files"""
    validation_status = {}
    
    try:
        # Check both input_dir and output directory for validation files
        directories_to_check = [input_dir, input_dir.parent / "output"]
        
        for base_dir in directories_to_check:
            if not base_dir.exists():
                continue
                
            _LOGGER.info(f"Looking for validation files in: {base_dir}")
            
            # Look for validation_status.json files in language directories
            for user_dir in base_dir.iterdir():
                if not user_dir.is_dir() or not user_dir.name.startswith('user_'):
                    continue
                    
                for lang_dir in user_dir.iterdir():
                    if not lang_dir.is_dir():
                        continue
                        
                    status_file = lang_dir / "validation_status.json"
                    if status_file.exists():
                        try:
                            with open(status_file, 'r', encoding='utf-8') as f:
                                status_data = json.load(f)
                            
                            _LOGGER.info(f"Found validation file: {status_file}")
                            
                            # Process each recording in the status file
                            for recording_key, recording_info in status_data.get("recordings", {}).items():
                                # Extract prompt_id from recording_key (format: "group_promptid")
                                prompt_id = recording_key.split('_')[-1]
                                
                                # Find the audio file
                                for root, dirs, files in os.walk(lang_dir):
                                    for file in files:
                                        if file.endswith(('.wav', '.webm')) and prompt_id in file:
                                            audio_path = Path(root) / file
                                            # Create relative key from input_dir
                                            relative_path = audio_path.relative_to(base_dir)
                                            # Convert to WAV format for export
                                            wav_path = str(relative_path).replace('.webm', '.wav')
                                            validation_status[wav_path] = {
                                                'status': recording_info.get('status', 'pending'),
                                                'validation_notes': recording_info.get('validation_notes', ''),
                                                'validated_by': recording_info.get('validated_by', ''),
                                                'validated_date': recording_info.get('validated_date', '')
                                            }
                                            _LOGGER.info(f"Mapped {wav_path} -> status: {recording_info.get('status', 'pending')}")
                                            break
                                    if wav_path in validation_status:
                                        break
                                        
                        except Exception as e:
                            _LOGGER.warning(f"Could not read validation file {status_file}: {e}")
                            continue
        
        _LOGGER.info(f"Loaded validation status for {len(validation_status)} recordings")
        return validation_status
        
    except Exception as e:
        _LOGGER.warning(f"Could not load validation status: {e}")
        return {}


def extract_speaker_info(audio_path: Path, input_dir: Path, user_mapping: dict) -> dict:
    """Extract speaker information from file path and database"""
    try:
        # Default speaker info
        speaker_info = {
            'speaker_id': 'unknown',
            'age': '',
            'gender': ''
        }
        
        # Try to extract user ID from path structure: user_X/language/prompt_group/
        path_parts = audio_path.relative_to(input_dir).parts
        user_id_str = None
        
        for part in path_parts:
            if part.startswith('user_'):
                user_id_str = part.replace('user_', '')
                break
        
        if user_id_str and user_id_str.isdigit():
            user_id = int(user_id_str)
            if user_id in user_mapping:
                # Use database information
                speaker_info = user_mapping[user_id].copy()
                _LOGGER.info(f"Found user {user_id} in database: {speaker_info}")
            else:
                # User not found in database, use path info
                speaker_info['speaker_id'] = f"user_{user_id}"
                _LOGGER.warning(f"User {user_id} not found in database, using path info")
        else:
            _LOGGER.warning(f"Could not extract user ID from path: {audio_path}")
        
        return speaker_info
        
    except Exception as e:
        _LOGGER.warning(f"Could not extract speaker info for {audio_path}: {e}")
        return {
            'speaker_id': 'unknown',
            'age': '',
            'gender': ''
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument(
        "--audio-glob", default="*.webm", help="Glob pattern for audio files"
    )
    #
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--samples-per-chunk", type=int, default=480)
    parser.add_argument("--keep-chunks-before", type=int, default=5)
    parser.add_argument("--keep-chunks-after", type=int, default=5)
    #
    parser.add_argument(
        "--skip-existing-wav",
        action="store_true",
        help="Don't overwrite existing WAV files",
    )
    #
    args = parser.parse_args()
    logging.basicConfig()

    if not shutil.which("ffmpeg"):
        _LOGGER.fatal("ffmpeg must be installed")
        return 1

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_dir = output_dir / "wav"

    # Load user information and validation status from database
    print("Loading user information and validation status from database...")
    user_mapping, recording_status = get_user_database_info()
    print(f"Loaded {len(user_mapping)} users and {len(recording_status)} recording statuses from database")

    export_audio = ExportAudio(user_mapping, recording_status)
    with open(
        output_dir / "metadata.csv", "w", encoding="utf-8"
    ) as metadata_file, ThreadPoolExecutor() as executor:
        # Write header with speaker metadata and validation status
        writer = csv.writer(metadata_file, delimiter=",")
        writer.writerow([
            "id", "text", "audio_file", "speaker_id", "age", "gender", "status"
        ])
        writer_lock = threading.Lock()
        for audio_path in input_dir.rglob(args.audio_glob):
            executor.submit(
                export_audio,
                audio_path,
                input_dir,
                wav_dir,
                writer,
                writer_lock,
                args,
            )


class ExportAudio:
    def __init__(self, user_mapping: dict, recording_status: dict):
        self.user_mapping = user_mapping
        self.recording_status = recording_status
        self.thread_data = threading.local()

    def __call__(
        self,
        audio_path: Path,
        input_dir: Path,
        wav_dir: Path,
        writer,
        writer_lock: threading.Lock,
        args: argparse.Namespace,
    ):
        try:
            text_path = audio_path.with_suffix(".txt")
            if not text_path.exists():
                _LOGGER.warning("Missing text file: %s", text_path)
                return

            if not hasattr(self.thread_data, "detector"):
                self.thread_data.detector = make_silence_detector()

            text = text_path.read_text(encoding="utf-8").strip()
            wav_path = wav_dir / audio_path.relative_to(input_dir).with_suffix(".wav")
            wav_id = wav_path.relative_to(wav_dir)

            if (not args.skip_existing_wav) or (
                (not wav_path.exists()) or (wav_path.stat().st_size == 0)
            ):
                if args.threshold <= 0:
                    offset_sec = 0.0
                    duration_sec = None
                else:
                    # Trim silence first.
                    #
                    # The VAD model works on 16khz, so we determine the portion of audio
                    # to keep and then just load that with librosa.
                    vad_sample_rate = 16000
                    audio_16khz_bytes = subprocess.check_output(
                        [
                            "ffmpeg",
                            "-i",
                            str(audio_path),
                            "-f",
                            "s16le",
                            "-acodec",
                            "pcm_s16le",
                            "-ac",
                            "1",
                            "-ar",
                            str(vad_sample_rate),
                            "pipe:",
                        ],
                        stderr=subprocess.DEVNULL,
                    )

                    # Normalize
                    audio_16khz = np.frombuffer(
                        audio_16khz_bytes, dtype=np.int16
                    ).astype(np.float32)
                    audio_16khz /= np.abs(np.max(audio_16khz))

                    offset_sec, duration_sec = trim_silence(
                        audio_16khz,
                        self.thread_data.detector,
                        threshold=args.threshold,
                        samples_per_chunk=args.samples_per_chunk,
                        sample_rate=vad_sample_rate,
                        keep_chunks_before=args.keep_chunks_before,
                        keep_chunks_after=args.keep_chunks_after,
                    )

                # Write as WAV
                command = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(audio_path),
                    "-f",
                    "wav",
                    "-acodec",
                    "pcm_s16le",
                    "-ss",
                    str(offset_sec),
                ]
                if duration_sec is not None:
                    command.extend(["-t", str(duration_sec)])

                command.append(str(wav_path))

                wav_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.check_call(command, stderr=subprocess.DEVNULL)

            with writer_lock:
                # Extract speaker information from database
                speaker_info = extract_speaker_info(audio_path, input_dir, self.user_mapping)
                
                # Get validation status from database
                # Use wav_id as key to match recording_status mapping
                rec_key = str(wav_id)  # This is already the relative path from wav folder
                validation_info = self.recording_status.get(rec_key, {})
                status = validation_info.get('status', 'pending')
                
                # Write row with essential metadata and validation status
                writer.writerow([
                    wav_id,                    # id (relative path from wav folder)
                    text,                       # text
                    str(wav_path.relative_to(wav_dir)),  # audio_file (relative from wav folder)
                    speaker_info['speaker_id'],   # speaker_id
                    speaker_info['age'],          # age
                    speaker_info['gender'],        # gender
                    status                       # validation status
                ])

            print(wav_path)
        except Exception:
            _LOGGER.exception("export_audio")


def make_silence_detector() -> SileroVoiceActivityDetector:
    silence_model = _DIR / "models" / "silero_vad.onnx"
    return SileroVoiceActivityDetector(silence_model)


if __name__ == "__main__":
    main()
