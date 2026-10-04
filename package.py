import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
output=root.parent/'ModelLedger-deployable.zip'
exclude={'.git','.venv','node_modules','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.runtime','.hypothesis','test-results','playwright-report','cache','dist','artifacts','build-info'}
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for path in sorted(root.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(root)
        if any(part in exclude for part in relative.parts):continue
        if path.name in {'.env','.env.production','.coverage','tsconfig.tsbuildinfo'} or path.suffix in {'.log','.db'}:continue
        archive.write(path,Path('modelledger')/relative)
print(f'{output} ({output.stat().st_size:,} bytes)')
