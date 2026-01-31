# Backchannel Candidates Web Viewer

A modern, clean web interface for reviewing backchannel candidates extracted from the SST corpus.

## Documentation

For a detailed, step-by-step description of how candidate backchannels were extracted and filtered, see [../docs/CANDIDATE_EXTRACTION.md](../docs/CANDIDATE_EXTRACTION.md).

## Features

- 🎨 **Color-coded confidence levels**: GREEN (HIGH), YELLOW (MEDIUM), RED (LOW)
- 🔊 **Audio playback**: Click play buttons to listen to utterances A and B
- 🎯 **Smart filtering**: Filter by confidence, token count, search text
- 📊 **Live statistics**: See distribution across confidence levels
- 🚩 **Warning flags**: Visual indicators for potential issues
- 📱 **Responsive design**: Works on desktop, tablet, and mobile

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the App

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and go to:
```
http://localhost:5000
```

## Usage

### Filters

- **Confidence**: Filter by HIGH/MEDIUM/LOW confidence levels
- **Tokens**: Set minimum/maximum token count range
- **Search**: Search in A and B utterance text
- **Reset**: Clear all filters

### Audio Playback

- Click the ▶ button next to any utterance to play its audio
- Button changes to ⏸ while playing
- Only one audio plays at a time

### Warning Flags

Cards show visual warnings for:
- **Has content**: B contains verbs, nouns, or adjectives (red)
- **Is question**: B is a multi-token question (orange)
- **After question**: B comes after A's question (pink)
- **A is backchannel**: A looks like a backchannel (yellow)

## Annotation Data

- Your annotation data is stored locally in `webapp/annotations.db`.
- This file is **not tracked by git** and will not be shared or overwritten.
- Each user has their own local annotation database.
- If you want to start fresh, simply delete `webapp/annotations.db` and it will be recreated automatically.

> **Note:** Do not commit your `annotations.db` to GitHub. If you want to share annotations, use the export feature or coordinate with your team.

## Development

The app structure:
- `app.py`: Flask backend with API endpoints
- `templates/index.html`: Main HTML template
- `static/css/style.css`: Styling
- `static/js/app.js`: Frontend JavaScript logic

To modify:
- **Colors/styles**: Edit `static/css/style.css`
- **Layout**: Edit `templates/index.html`
- **Functionality**: Edit `static/js/app.js`
- **Backend/API**: Edit `app.py`
