import os
import json
import csv
import zipfile
import io
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
from datetime import datetime
from quart import current_app, send_file

class DatasetExporter:
    """Handles exporting of recorded datasets in various formats."""
    
    def __init__(self, output_dir: Union[str, Path]):
        self.output_dir = Path(output_dir)
        
    def get_available_datasets(self) -> List[Dict]:
        """Get a list of all available datasets."""
        datasets = []
        if not self.output_dir.exists():
            return datasets
            
        for lang_dir in self.output_dir.iterdir():
            if lang_dir.is_dir():
                audio_files = list(lang_dir.glob("**/*.wav")) + list(lang_dir.glob("**/*.mp3"))
                if audio_files:
                    datasets.append({
                        'language': lang_dir.name,
                        'recordings_count': len(audio_files),
                        'last_modified': datetime.fromtimestamp(lang_dir.stat().st_mtime).isoformat()
                    })
        return datasets
    
    def export_dataset(self, 
                      language: str, 
                      format: str = 'zip',
                      include_metadata: bool = True) -> BinaryIO:
        """
        Export a dataset for a specific language.
        
        Args:
            language: Language code (directory name)
            format: Export format ('zip', 'csv', 'json')
            include_metadata: Whether to include metadata files
            
        Returns:
            File-like object containing the exported data
        """
        lang_dir = self.output_dir / language
        if not lang_dir.exists():
            raise FileNotFoundError(f"No dataset found for language: {language}")
        
        if format == 'zip':
            return self._export_as_zip(lang_dir, include_metadata)
        elif format == 'csv':
            return self._export_as_csv(lang_dir, include_metadata)
        elif format == 'json':
            return self._export_as_json(lang_dir, include_metadata)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_as_zip(self, lang_dir: Path, include_metadata: bool) -> BinaryIO:
        """Export dataset as a ZIP file."""
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add audio files
            for audio_file in lang_dir.rglob('*.wav'):
                zf.write(audio_file, audio_file.relative_to(self.output_dir))
            for audio_file in lang_dir.rglob('*.mp3'):
                zf.write(audio_file, audio_file.relative_to(self.output_dir))
                
            # Add metadata if requested
            if include_metadata:
                # Look for both CSV and JSON metadata files
                for meta_file in lang_dir.rglob('metadata.*'):
                    if meta_file.suffix in ['.csv', '.json']:
                        zf.write(meta_file, meta_file.relative_to(self.output_dir))
                
                # Also include validation files if they exist
                for meta_file in lang_dir.rglob('validation.*'):
                    if meta_file.suffix in ['.csv', '.json']:
                        zf.write(meta_file, meta_file.relative_to(self.output_dir))
        
        memory_file.seek(0)
        return memory_file
    
    def _export_as_csv(self, lang_dir: Path, include_metadata: bool) -> BinaryIO:
        """Export dataset as a CSV file."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Process metadata file if exists (check both CSV and JSON)
        metadata_file = None
        for ext in ['.csv', '.json']:
            potential_file = lang_dir / f'metadata{ext}'
            if potential_file.exists():
                metadata_file = potential_file
                break
        
        if metadata_file:
            if metadata_file.suffix == '.csv':
                # If it's already a CSV, just copy its content
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    output.write(content)
            else:
                # If it's JSON, convert to CSV
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                # Write header for simplified format with validation status
                writer.writerow([
                    'id', 'text', 'audio_file', 'speaker_id', 'age', 'gender', 'status'
                ])
                
                for rec_id, rec_data in metadata.items():
                    writer.writerow([
                        rec_id,
                        rec_data.get('text', ''),
                        rec_data.get('audio_file', ''),  # This should already be relative from wav folder
                        rec_data.get('speaker_id', ''),
                        rec_data.get('age', ''),
                        rec_data.get('gender', ''),
                        rec_data.get('status', 'pending')  # Add validation status
                    ])
        else:
            # Write header even if no metadata exists
            writer.writerow([
                'id', 'text', 'audio_file', 'speaker_id', 'age', 'gender', 'status'
            ])
        
        # Convert to bytes and return
        output.seek(0)
        return io.BytesIO(output.getvalue().encode('utf-8'))
    
    def _export_as_json(self, lang_dir: Path, include_metadata: bool) -> BinaryIO:
        """Export dataset as a JSON file."""
        result = {
            'language': lang_dir.name,
            'recordings': [],
            'metadata': {}
        }
        
        # Process metadata file if exists (check both CSV and JSON)
        metadata_file = None
        for ext in ['.csv', '.json']:
            potential_file = lang_dir / f'metadata{ext}'
            if potential_file.exists():
                metadata_file = potential_file
                break
        
        if metadata_file:
            if metadata_file.suffix == '.json':
                # If it's JSON, load directly
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    result['recordings'] = [
                        {'id': k, **v} for k, v in json.load(f).items()
                    ]
            else:
                # If it's CSV, convert to JSON format
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    header = next(reader)  # Skip header
                    for row in reader:
                        if len(row) >= 2:  # At least id and text
                            recording_data = {
                                'id': row[0],
                                'text': row[1] if len(row) > 1 else '',
                                'audio_file': row[2] if len(row) > 2 else '',  # Should be relative from wav folder
                                'speaker_id': row[3] if len(row) > 3 else '',
                            }
                            # Add essential speaker metadata if available
                            if len(row) > 4:
                                recording_data['age'] = row[4] if len(row) > 4 else ''
                            if len(row) > 5:
                                recording_data['gender'] = row[5] if len(row) > 5 else ''
                            # Add validation status if available
                            if len(row) > 6:
                                recording_data['status'] = row[6] if len(row) > 6 else 'pending'
                            
                            result['recordings'].append(recording_data)
        
        # Include validation data if requested
        if include_metadata:
            for ext in ['.csv', '.json']:
                validation_file = lang_dir / f'validation{ext}'
                if validation_file.exists():
                    with open(validation_file, 'r', encoding='utf-8') as f:
                        if validation_file.suffix == '.json':
                            result['validation'] = json.load(f)
                        else:
                            # Convert CSV validation to JSON format
                            reader = csv.reader(f)
                            header = next(reader)
                            result['validation'] = [
                                dict(zip(header, row)) for row in reader
                            ]
                    break
        
        # Convert to bytes and return
        return io.BytesIO(json.dumps(result, indent=2, ensure_ascii=False).encode('utf-8'))
    
    def get_export_filename(self, language: str, format: str) -> str:
        """Generate a filename for the exported dataset."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if format == 'zip':
            return f"{language}_dataset_{timestamp}.zip"
        elif format == 'csv':
            return f"{language}_metadata_{timestamp}.csv"
        elif format == 'json':
            return f"{language}_dataset_{timestamp}.json"
        else:
            return f"{language}_export_{timestamp}.{format}"
