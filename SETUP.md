# Setup Instructions

## Prerequisites
- Python 3.10 or higher
- pip package manager
- Google Gemini API key (optional - mock mode available)

## Installation

1. Clone or download this repository:
   ```bash
   git clone https://github.com/bhavikakothari3-cloud/Ai-soc-incident-triage.git
   cd Ai-soc-incident-triage
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # source venv/bin/activate  # On macOS/Linux
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure API Key (Optional):
   
   For full functionality, you need a Google Gemini API key:
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a `.env` file in the project root:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```
   - If no API key is provided, the app will run in mock mode with simulated responses

5. Run the application:
   ```bash
   streamlit run app.py
   ```

6. Access the application at:
   - http://localhost:8501

## Project Structure
```
AI_Incident_Triage_System/
├── app.py                 # Main Streamlit application
├── database.py            # SQLite database operations
├── llm.py                 # LLM integration (Gemini API)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── SETUP.md              # This file
└── README.md             # Project overview
```

## Features Implemented
- Dashboard with alert statistics
- Alert submission form
- AI-powered incident analysis with structured output
- SQLite database for alert persistence
- Alert history with search and filtering
- MITRE ATT&CK technique mapping
- Confidence scoring and escalation recommendations