import json
from pathlib import Path
from app.main import app
path=Path(__file__).resolve().parents[1]/'docs/openapi.json'
path.write_text(json.dumps(app.openapi(),indent=2)+'\n')
print('OpenAPI schema exported')
