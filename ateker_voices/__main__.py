import argparse
import asyncio
import csv
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from uuid import uuid4

import hypercorn
from quart import (
    Quart,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

_LOGGER = logging.getLogger(__name__)
_DIR = Path(__file__).parent


@dataclass
class Prompt:
    """Single prompt for the user to read."""

    group: str
    id: str
    text: str


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=80)
    #
    parser.add_argument(
        "--prompts",
        help="Path to prompts directory",
        action="append",
        default=[_DIR.parent / "prompts"],
    )
    parser.add_argument(
        "--output",
        help="Path to output directory",
        default=_DIR.parent / "output",
    )
    #
    parser.add_argument(
        "--multi-user",
        action="store_true",
        help="Require login code and user output directory to exist",
    )
    parser.add_argument("--cc0", action="store_true", help="Show public domain notice")
    #
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to console"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    # Make output_dir available globally for route handlers
    global output_dir
    output_dir = Path(args.output)

    prompts_dirs = [Path(p) for p in args.prompts]
    css_dir = _DIR / "css"
    js_dir = _DIR / "js"
    img_dir = _DIR / "img"
    webfonts_dir = _DIR / "webfonts"

    # Define only Ateker languages
    ateker_languages = {
        'Ngakarimojong': 'kdj',
        'Ateso': 'teo', 
        'Soo (Tepes)': 'teu',
        'Ik (Icétot)': 'ikx'
    }
    
    prompts, languages = load_prompts(prompts_dirs)
    
    # Filter to only Ateker languages
    filtered_languages = {name: code for name, code in languages.items() if name in ateker_languages}

    app = Quart("crest-recording-studio", template_folder=str(_DIR / "templates"))
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 mb
    app.secret_key = str(uuid4())

    @app.route("/")
    @app.route("/index.html")
    async def api_index() -> str:
        """Main page"""
        return await render_template(
            "index.html",
            languages=sorted(filtered_languages.items()),
            multi_user=args.multi_user,
            cc0=args.cc0,
        )

    @app.route("/done.html")
    async def api_done() -> str:
        return await render_template("done.html")

    @app.route("/record")
    async def api_record() -> str:
        """Record audio for a text prompt"""
        language = request.args["language"]

        if args.multi_user:
            user_id = request.args.get("userId")
            audio_dir = output_dir / f"user_{user_id}"
            user_dir = audio_dir / language
            if not user_dir.is_dir():
                _LOGGER.warning("No user/language directory: %s", user_dir)
                user_id = None
        else:
            user_id = None
            audio_dir = output_dir

        next_prompt, num_complete, num_items = get_next_prompt(
            prompts,
            audio_dir,
            language,
        )
        if next_prompt is None:
            return await render_template("done.html")

        complete_percent = 100 * (num_complete / num_items if num_items > 0 else 1)
        return await render_template(
            "record.html",
            language=language,
            prompt_group=next_prompt.group,
            prompt_id=next_prompt.id,
            text=next_prompt.text,
            num_complete=num_complete,
            num_items=num_items,
            complete_percent=complete_percent,
            multi_user=args.multi_user,
            user_id=user_id,
        )

    @app.route("/submit", methods=["POST"])
    async def api_submit() -> Response:
        """Submit audio for a text prompt"""
        form = await request.form
        language = form["language"]
        prompt_group = form["promptGroup"]
        prompt_id = form["promptId"]
        prompt_text = form["text"]
        audio_format = form["format"]

        files = await request.files
        assert "audio" in files, "No audio"

        suffix = ".webm"
        if "wav" in audio_format:
            suffix = ".wav"

        # Initialize user_id for all cases
        user_id = None

        if args.multi_user:
            user_id = form["userId"]
            user_dir = output_dir / f"user_{user_id}"
            if not user_dir.is_dir():
                _LOGGER.warning("No user/language directory: %s", user_dir)
                raise ValueError("Invalid login code")

            audio_dir = user_dir
        else:
            audio_dir = output_dir

        # Save audio and transcription
        audio_path = audio_dir / language / prompt_group / f"{prompt_id}{suffix}"
        _LOGGER.debug("Saving to %s", audio_path)

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        await files["audio"].save(audio_path)

        text_path = audio_path.parent / f"{prompt_id}.txt"
        text_path.write_text(prompt_text, encoding="utf-8")

        # Create status file for validation tracking (single file per language)
        status_file = audio_dir / language / "validation_status.json"
        if not status_file.exists():
            # Initialize validation status file for this language
            status_data = {
                "language": language,
                "recordings": {}
            }
        else:
            status_data = json.loads(status_file.read_text(encoding="utf-8"))

        # Add this recording to the status file
        recording_key = f"{prompt_group}_{prompt_id}"
        status_data["recordings"][recording_key] = {
            "recording_id": f"{language}_{prompt_group}_{prompt_id}",
            "language": language,
            "user_id": user_id or "anonymous",
            "prompt": prompt_text,
            "audio_format": audio_format,
            "submitted_date": datetime.now().isoformat(),
            "duration": form.get("duration", "unknown"),
            "status": "pending",
            "validation_notes": "",
            "validated_by": "",
            "validated_date": ""
        }

        # Save updated status file
        status_file.write_text(json.dumps(status_data, indent=2), encoding="utf-8")

        # Get next prompt
        next_prompt, num_complete, num_items = get_next_prompt(
            prompts,
            audio_dir,
            language,
        )
        if next_prompt is None:
            return jsonify({"done": True})

        complete_percent = 100 * (num_complete / num_items if num_items > 0 else 1)
        return jsonify(
            {
                "done": False,
                "promptGroup": next_prompt.group,
                "promptId": next_prompt.id,
                "promptText": next_prompt.text,
                "numComplete": num_complete,
                "numItems": num_items,
                "completePercent": complete_percent,
            }
        )

    @app.route("/upload")
    async def api_upload() -> str:
        """Upload an existing dataset"""
        language = request.args["language"]

        if args.multi_user:
            user_id = request.args.get("userId")
            audio_dir = output_dir / f"user_{user_id}"
            user_dir = audio_dir / language
            if not user_dir.is_dir():
                _LOGGER.warning("No user/language directory: %s", user_dir)
                raise RuntimeError("Invalid login code")
        else:
            user_id = None
            audio_dir = output_dir

        return await render_template(
            "upload.html",
            language=language,
            multi_user=args.multi_user,
            user_id=user_id,
        )

    @app.route("/dataset", methods=["POST"])
    async def api_dataset() -> str:
        """Upload an existing dataset"""
        form = await request.form
        language = form["language"]

        if args.multi_user:
            user_id = form.get("userId")
            audio_dir = output_dir / f"user_{user_id}"
            user_dir = audio_dir / language
            if not user_dir.is_dir():
                _LOGGER.warning("No user/language directory: %s", user_dir)
                raise RuntimeError("Invalid login code")
        else:
            user_id = None
            audio_dir = output_dir

        files = await request.files
        dataset_file = files["dataset"]
        upload_path = user_dir / "_uploads" / Path(dataset_file.filename).name
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        await dataset_file.save(upload_path)
        _LOGGER.debug("Saved dataset to %s", upload_path)

        return await render_template("done.html")

    @app.route("/admin")
    async def api_admin() -> str:
        """Admin interface"""
        return await render_template(
            "admin.html",
            languages=sorted(filtered_languages.items()),
        )

    @app.route("/admin/validation")
    async def api_admin_validation() -> str:
        """Data validation interface"""
        # Load real validation data from saved recordings (only Ateker languages)
        validation_data = load_validation_data(output_dir, ateker_languages.keys())

        return await render_template(
            "admin_validation.html",
            languages=sorted(ateker_languages.items()),
            validation_data=validation_data,
        )

    @app.route("/admin/prompts")
    async def api_admin_prompts() -> str:
        """Prompt management interface"""
        language = request.args.get("language", "")
        language_prompts = None
        if language and language in prompts:
            language_prompts = prompts[language]
            # Group prompts by category
            prompt_groups = defaultdict(list)
            for prompt in language_prompts:
                prompt_groups[prompt.group].append(prompt)
        else:
            prompt_groups = {}

        return await render_template(
            "admin_prompts.html",
            language=language,
            prompts=language_prompts,
            languages=sorted(filtered_languages.items()),
            prompt_groups=dict(prompt_groups),
        )

    @app.route("/admin/add_prompt", methods=["POST"])
    async def api_add_prompt() -> Response:
        """Add a new prompt"""
        form = await request.form
        language = form["language"]
        category = form["category"]
        prompt_text = form["text"]
        
        if not language or not category or not prompt_text:
            return jsonify({"error": "Missing required fields"}), 400
            
        # Generate new prompt ID with crestai prefix for Ugandan languages
        existing_prompts = prompts.get(language, [])
        max_id = 0
        
        # Check if this is a Ugandan language (ends with -UG)
        is_ugandan_lang = language.endswith('-UG')
        
        for prompt in existing_prompts:
            try:
                if is_ugandan_lang and prompt.id.startswith('crestai'):
                    # Extract number from crestai prefix
                    prompt_id_num = int(prompt.id.replace('crestai', ''))
                    max_id = max(max_id, prompt_id_num)
                elif not is_ugandan_lang:
                    # For non-Ugandan languages, use numeric IDs
                    prompt_id_num = int(prompt.id)
                    max_id = max(max_id, prompt_id_num)
            except ValueError:
                continue
        
        # Generate new ID based on language type
        if is_ugandan_lang:
            new_id = f"crestai{max_id + 1:04d}"
        else:
            new_id = str(max_id + 1)
        
        # Add to memory
        new_prompt = Prompt(group=category, id=new_id, text=prompt_text)
        prompts[language].append(new_prompt)
        
        # Save to file
        language_name = None
        for name, code in languages.items():
            if code == language:
                language_name = name
                break
                
        if language_name:
            prompt_file = prompts_dirs[0] / f"{language_name}_{language}" / f"{category}.txt"
            prompt_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing prompts from file
            existing_lines = []
            if prompt_file.exists():
                existing_lines = prompt_file.read_text(encoding="utf-8").strip().split("\n")
            
            # Add new prompt
            existing_lines.append(f"{new_id}\t{prompt_text}")
            
            # Write back to file
            prompt_file.write_text("\n".join(existing_lines), encoding="utf-8")
        
        return jsonify({"success": True, "id": new_id})

    @app.route("/admin/delete_prompt", methods=["POST"])
    async def api_delete_prompt() -> Response:
        """Delete a prompt"""
        form = await request.form
        language = form["language"]
        category = form["category"]
        prompt_id = form["id"]
        
        # Remove from memory
        if language in prompts:
            prompts[language] = [p for p in prompts[language] 
                               if not (p.group == category and p.id == prompt_id)]
        
        # Update file
        language_name = None
        for name, code in languages.items():
            if code == language:
                language_name = name
                break
                
        if language_name:
            prompt_file = prompts_dirs[0] / f"{language_name}_{language}" / f"{category}.txt"
            if prompt_file.exists():
                lines = prompt_file.read_text(encoding="utf-8").strip().split("\n")
                updated_lines = []
                for line in lines:
                    if line.strip():
                        parts = line.split("\t", 1)
                        if len(parts) >= 2 and parts[0] != prompt_id:
                            updated_lines.append(line)
                        elif len(parts) == 1 and prompt_id != str(len(updated_lines)):
                            updated_lines.append(line)
                
                prompt_file.write_text("\n".join(updated_lines), encoding="utf-8")
        
        return jsonify({"success": True})

    @app.route("/admin/validate_recording", methods=["POST"])
    async def api_validate_recording() -> Response:
        """Update validation status for a recording"""
        form = await request.form
        recording_id = form["recording_id"]
        status = form["status"]
        notes = form.get("notes", "")

        if status not in ["approved", "rejected"]:
            return jsonify({"error": "Invalid status"}), 400

        # Find and update the recording in validation status files
        updated = False

        # Scan all language directories for validation status files
        for language_dir in output_dir.iterdir():
            if not language_dir.is_dir():
                continue

            # Skip user directories (they have "user_" prefix)
            if language_dir.name.startswith("user_"):
                for user_language_dir in language_dir.iterdir():
                    if user_language_dir.is_dir():
                        updated = _update_recording_status(user_language_dir, recording_id, status, notes)
                        if updated:
                            break
            else:
                # Single user mode
                updated = _update_recording_status(language_dir, recording_id, status, notes)

            if updated:
                break

        if not updated:
            return jsonify({"error": "Recording not found"}), 404

        return jsonify({"success": True})

    @app.errorhandler(Exception)
    async def handle_error(err) -> Tuple[str, int]:
        """Return error as text."""
        _LOGGER.exception(err)
        return (f"{err.__class__.__name__}: {err}", 500)

    @app.route("/css/<path:filename>", methods=["GET"])
    async def css(filename) -> Response:
        """CSS static endpoint."""
        return await send_from_directory(css_dir, filename)

    @app.route("/js/<path:filename>", methods=["GET"])
    async def js(filename) -> Response:
        """Javascript static endpoint."""
        return await send_from_directory(js_dir, filename)

    @app.route("/img/<path:filename>", methods=["GET"])
    async def img(filename) -> Response:
        """Image static endpoint."""
        return await send_from_directory(img_dir, filename)

    @app.route("/webfonts/<path:filename>", methods=["GET"])
    async def webfonts(filename) -> Response:
        """Webfonts static endpoint."""
        return await send_from_directory(webfonts_dir, filename)

    @app.route("/<path:filepath>", methods=["GET"])
    async def serve_output_files(filepath) -> Response:
        """Serve files from the output directory for validation playback."""
        # Security check - only allow files within the output directory
        output_path = output_dir / filepath
        if not str(output_path).startswith(str(output_dir)):
            return Response("Forbidden", status=403)

        if output_path.exists() and output_path.is_file():
            return await send_from_directory(output_dir, filepath)
        else:
            return Response("File not found", status=404)

    @app.route("/templates/<path:filename>", methods=["GET"])
    async def templates(filename) -> Response:
        """Serve template files for download."""
        from quart import Response
        import hypercorn
        templates_dir = _DIR / "templates"

        # Set correct MIME type for CSV files
        if filename.endswith('.csv'):
            return await send_from_directory(templates_dir, filename, mimetype='text/csv')
        else:
            return await send_from_directory(templates_dir, filename)

    # Run web server
    hyp_config = hypercorn.config.Config()
    hyp_config.bind = [f"{args.host}:{args.port}"]

    asyncio.run(hypercorn.asyncio.serve(app, hyp_config))


# -----------------------------------------------------------------------------


def load_prompts(
    prompts_dirs: List[Path],
) -> Tuple[Dict[str, List[Prompt]], Dict[str, str]]:
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
                    _load_language_validation_data(user_language_dir, validation_data)
        else:
            # Single user mode - only load if language is allowed
            if language_dir.name in allowed_languages:
                _load_language_validation_data(language_dir, validation_data)

    return validation_data

def _load_language_validation_data(language_dir: Path, validation_data: List[Dict]):
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

def _update_recording_status(language_dir: Path, recording_id: str, status: str, notes: str) -> bool:
    """Update validation status for a specific recording in a language directory."""
    status_file = language_dir / "validation_status.json"
    if not status_file.exists():
        return False

    try:
        status_data = json.loads(status_file.read_text(encoding="utf-8"))

        # Find the recording in the status file
        for recording_key, recording_info in status_data.get("recordings", {}).items():
            if recording_info.get("recording_id") == recording_id:
                # Update the recording status
                recording_info["status"] = status
                recording_info["validation_notes"] = notes
                recording_info["validated_by"] = "admin"  # Could be enhanced with actual user
                recording_info["validated_date"] = datetime.now().isoformat()

                # Save updated status file
                status_file.write_text(json.dumps(status_data, indent=2), encoding="utf-8")
                return True

    except (json.JSONDecodeError, KeyError) as e:
        _LOGGER.warning("Error updating validation status file %s: %s", status_file, e)

    return False

def get_language_name(language_code: str) -> str:
    """Convert language code to language name."""
    language_names = {
        'eng': 'English',
        'swh': 'Swahili',
        'lug': 'Luganda',
        'cgg': 'Chiga',
        'rub': 'Gungu',
        'gwr': 'Gwere',
        'koo': 'Konzo',
        'myx': 'Masaaba',
        'nyn': 'Nyankore',
        'nuj': 'Nyungwe',
        'nyo': 'Nyoro',
        'ruc': 'Ruuli',
        'xog': 'Soga',
        'ttj': 'Tooro',
        'ach': 'Acholi',
        'adh': 'Adhola',
        'alz': 'Alur',
        'luc': 'Aringa',
        'teo': 'Teso',
        'ikx': 'Ik',
        'keo': 'Kakwa',
        'kdj': 'Karamojong',
        'kdi': 'Kumam',
        'laj': 'Lango',
        'lgg': 'Lugbara',
        'mhi': 'Ma\'di',
        'kcn': 'Nubi',
        'dno': 'Ndo',
        'teu': 'Tepeth'
    }
    return language_names.get(language_code, language_code.upper())

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


# -----------------------------------------------------------------------------


if __name__ == "__main__":
    main()
