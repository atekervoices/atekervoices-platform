import csv
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

_LOGGER = logging.getLogger(__name__)

@dataclass
class Prompt:
    """Single prompt for the user to read."""
    group: str
    id: str
    text: str


def load_prompts(prompts_dirs: List[Path]) -> Tuple[Dict[str, List[Prompt]], Dict[str, str]]:
    prompts = defaultdict(list)
    languages = {}

    # Only process Ateker languages
    ateker_codes = {'kdj', 'teo', 'teu', 'ikx'}

    for prompts_dir in prompts_dirs:
        for language_dir in prompts_dir.iterdir():
            if not language_dir.is_dir():
                continue

            try:
                name, code = language_dir.name.rsplit("_", maxsplit=1)
                # Only process Ateker languages
                if code in ateker_codes:
                    languages[name] = code
                    for prompt_path in language_dir.glob("*.txt"):
                        _LOGGER.debug("Loading prompts from %s", prompt_path)
                        prompt_group = prompt_path.stem
                        with open(prompt_path, "r", encoding="utf-8") as prompt_file:
                            reader = csv.reader(prompt_file, delimiter="\t")
                            for i, row in enumerate(reader):
                                # Skip empty rows
                                if not row or len(row) == 0:
                                    continue
                                
                                if len(row) == 1:
                                    prompt_id = str(i)
                                else:
                                    prompt_id = row[0]

                                prompts[code].append(
                                    Prompt(group=prompt_group, id=prompt_id, text=row[-1])
                                )
            except ValueError:
                # Skip directories that don't follow the naming convention
                continue

    return prompts, languages


def load_validation_data(output_dir: Path, allowed_languages: List[str] = None) -> List[Dict]:
    """Load validation data from validation status files."""
    validation_data = []
    
    if allowed_languages is None:
        allowed_languages = []  # If no languages specified, return empty list

    # Scan all language directories for validation status files
    for language_dir in output_dir.iterdir():
        if not language_dir.is_dir():
            continue

        # Skip user directories (they have "user_" prefix)
        if language_dir.name.startswith("user_"):
            for user_language_dir in language_dir.iterdir():
                if user_language_dir.is_dir() and user_language_dir.name in allowed_languages:
                    _load_language_validation_data(user_language_dir, validation_data, output_dir)
        else:
            # Single user mode - only load if language is allowed
            if language_dir.name in allowed_languages:
                _load_language_validation_data(language_dir, validation_data, output_dir)

    return validation_data


def _load_language_validation_data(language_dir: Path, validation_data: List[Dict], output_dir: Path):
    """Load validation data for a specific language directory."""
    status_file = language_dir / "validation_status.json"
    if not status_file.exists():
        return

    try:
        status_data = json.loads(status_file.read_text(encoding="utf-8"))

        # Process each recording in the status file
        for recording_key, recording_info in status_data.get("recordings", {}).items():
            # Find the audio file - extract prompt_id from recording_key (format: "group_promptid")
            prompt_id = recording_key.split('_')[-1]  # Get the last part after underscore
            audio_file = None
            
            for root, dirs, files in os.walk(language_dir):
                for file in files:
                    if file.endswith(('.wav', '.webm')) and prompt_id in file:
                        audio_file = Path(root) / file
                        break
                if audio_file:
                    break

            if audio_file and audio_file.exists():
                # Add language name for display - use simple uppercase conversion
                recording_info["language_name"] = recording_info["language"].upper()
                recording_info["audio_path"] = str(audio_file.relative_to(output_dir))
                validation_data.append(recording_info)

    except (json.JSONDecodeError, KeyError) as e:
        _LOGGER.warning("Error reading validation status file %s: %s", status_file, e)


def get_next_prompt(
    prompts: Dict[str, List[Prompt]],
    output_dir: Path,
    language: str,
):
    language_prompts = prompts[language]
    language_dir = output_dir / language
    incomplete_prompts = []
    for prompt in language_prompts:
        text_path = language_dir / prompt.group / f"{prompt.id}.txt"
        if not text_path.exists():
            incomplete_prompts.append(prompt)

    num_items = len(language_prompts)
    num_complete = num_items - len(incomplete_prompts)

    if incomplete_prompts:
        next_prompt = incomplete_prompts[0]
    else:
        next_prompt = None

    return next_prompt, num_complete, num_items
