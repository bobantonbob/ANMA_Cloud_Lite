"""Create an explicit allowlisted source bundle, never a copy of the workspace."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
DIRECTORIES=['anma_cloud','dashboard','templates','static','docs','.github','tools',
             'ha_integration/custom_components','ha_integration/tools','ha_integration/tests']
FILES=['README.md','requirements.txt','requirements-dev.txt','requirements.lock','manage.py',
       'Dockerfile','docker-compose.yml','.gitignore','.dockerignore','.env.example',
       'ha_integration/README_UA.md','tests/check_ui.cjs']

if __name__=='__main__':
    target=ROOT/'ANMA_Cloud_Lite_source_v0.4.2.zip'
    paths={ROOT/name for name in FILES}
    for directory in DIRECTORIES:
        paths.update(path for path in (ROOT/directory).rglob('*') if path.is_file()
                     and '__pycache__' not in path.parts and path.suffix not in ('.pyc','.sqlite3','.log'))
    env = dotenv_values(ROOT/'.env')
    secret_values = [env.get(key) for key in ('DJANGO_SECRET_KEY','HA_TOKEN','GOOGLE_CLIENT_SECRET','ANMA_CONNECTION_KEY')]
    for path in paths:
        if path.is_file() and any(value and len(value)>12 and value.encode() in path.read_bytes() for value in secret_values):
            raise RuntimeError('Configured secret found in source file: '+str(path.relative_to(ROOT)))
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            if path.is_file():archive.write(path,path.relative_to(ROOT))
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        assert not any(Path(name).name=='.env' or name.endswith(('.sqlite3','.log')) for name in archive.namelist())
    print(target)
