"""Verify wheel ownership before running the independent Simulator test suite."""
import argparse
import base64
import csv
from email.parser import Parser
import io
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import sys
from zipfile import ZipFile

try:
    from scripts.contracts_artifact import NAME as CONTRACTS_NAME, VERSION as CONTRACTS_VERSION, installed_provenance
except ModuleNotFoundError:
    from contracts_artifact import NAME as CONTRACTS_NAME, VERSION as CONTRACTS_VERSION, installed_provenance


def verify_selected_wheel(wheel, artifact):
    wheel=Path(wheel)
    if not wheel.is_absolute() or wheel.suffix!='.whl':
        raise ValueError('The selected wheel must be an absolute wheel path.')
    payload=wheel.read_bytes()
    digest=hashlib.sha256(payload).hexdigest()
    direct=json.loads(artifact.read_text('direct_url.json') or '{}')
    archive_info=direct.get('archive_info',{})
    installed_digest=archive_info.get('hashes',{}).get('sha256')
    if installed_digest is None and archive_info.get('hash','').startswith('sha256='):
        installed_digest=archive_info['hash'].split('=',1)[1]
    if installed_digest!=digest:
        raise ValueError('Installed Simulator archive digest differs from the selected wheel; force reinstall the selected wheel.')
    prefix='cirnet_simulator-0.1.2.dist-info/'
    expected={'cirnet_sim/'+name+'.py' for name in ('__init__','analog','circuit','dispatch','engine','logic','nets','waveform','backends')}
    expected.add('netcircuit_sim/__init__.py')
    expected.update(prefix+name for name in ('licenses/LICENSE','METADATA','WHEEL','top_level.txt','RECORD'))
    with ZipFile(io.BytesIO(payload)) as archive:
        if len(archive.namelist())!=len(expected) or set(archive.namelist())!=expected:
            raise ValueError('Unexpected selected wheel payload inventory.')
        metadata=Parser().parsestr(archive.read(prefix+'METADATA').decode('utf-8'))
        if metadata['Name']!='cirnet-simulator' or metadata['Version']!='0.1.2':
            raise ValueError('The selected wheel must contain cirnet-simulator==0.1.2.')
        dependencies = {entry.replace(' ', '') for entry in metadata.get_all('Requires-Dist', []) if ';' not in entry}
        if dependencies != {f'{CONTRACTS_NAME}=={CONTRACTS_VERSION}', 'jsonschema==4.26.0'}:
            raise ValueError('Simulator runtime dependency pins differ from the current source build.')
        selected_records={row[0]:row[1:] for row in csv.reader(io.StringIO(archive.read(prefix+'RECORD').decode('utf-8')))}
        installed_records={row[0]:row[1:] for row in csv.reader(io.StringIO(artifact.read_text('RECORD') or ''))}
        if set(selected_records)!=expected:
            raise ValueError('The selected wheel RECORD inventory differs from its archive.')
        for name in expected-{prefix+'RECORD'}:
            # pip adds INSTALLER/direct_url and may compiled-file entries to
            # RECORD, so compare each selected original row and payload.
            if installed_records.get(name)!=selected_records[name]:
                raise ValueError('Installed RECORD differs from the selected wheel: '+name)
            if Path(artifact.locate_file(name)).read_bytes()!=archive.read(name):
                raise ValueError('Installed payload differs from the selected wheel: '+name)
    return {'selected_sha256':digest,'selected_files':len(expected),'selected_payload_files':len(expected)-1}


def check_installed(*,wheel=None):
    import cirnet_sim
    artifact=distribution('cirnet-simulator')
    if artifact.version!='0.1.2':
        raise ValueError('Expected cirnet-simulator==0.1.2.')
    if not artifact.read_text('WHEEL') or not artifact.read_text('RECORD'):
        raise ValueError('Simulator distribution is shadowed by source metadata.')
    direct=json.loads(artifact.read_text('direct_url.json') or '{}')
    if 'dir_info' in direct:
        raise ValueError('Simulator requires a wheel; editable/source-directory installs are unsupported.')
    entry=Path(artifact.locate_file('cirnet_sim/__init__.py')).resolve()
    if Path(cirnet_sim.__file__).resolve()!=entry:
        raise ValueError('Simulator imports are shadowed by source.')
    import netcircuit_sim
    if netcircuit_sim is not cirnet_sim:
        raise ValueError('Legacy Simulator imports must resolve to the canonical package.')
    owned=[]
    for item in artifact.files or ():
        if not str(item).replace('\\','/').startswith(('cirnet_sim/', 'netcircuit_sim/')) or item.suffix=='.pyc':
            continue
        target=Path(artifact.locate_file(item)).resolve()
        if not target.is_relative_to(entry.parent.parent / str(item).replace('\\','/').split('/')[0]) or not target.is_file() or item.hash is None or item.hash.mode!='sha256':
            raise ValueError('Simulator package lacks valid wheel RECORD ownership: '+str(item))
        digest=base64.urlsafe_b64encode(hashlib.sha256(target.read_bytes()).digest()).rstrip(b'=').decode()
        if digest!=item.hash.value:
            raise ValueError('Simulator package differs from wheel RECORD: '+str(item))
        owned.append(str(item))
    if set(owned)!=({'cirnet_sim/'+name+'.py' for name in ('__init__','analog','circuit','dispatch','engine','logic','nets','waveform','backends')} | {'netcircuit_sim/__init__.py'}):
        raise ValueError('Expected the exact nine-module Simulator runtime and legacy import shim inventory.')
    for name,module in tuple(sys.modules.items()):
        if name in ('cirnet_sim', 'netcircuit_sim') or name.startswith(('cirnet_sim.', 'netcircuit_sim.')):
            origin=getattr(module,'__file__',None)
            if origin and not Path(origin).resolve().is_relative_to(entry.parent):
                raise ValueError('Simulator submodule imports are shadowed by source: '+name)
    result={'simulator':{'version':artifact.version,'root':str(entry.parent),'owned_files':len(owned)},
            'contracts':installed_provenance()}
    if wheel is not None:result['simulator'].update(verify_selected_wheel(wheel,artifact))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel',type=Path,help='Bind verification to this newly built archive, including its digest and metadata payload.')
    args=parser.parse_args()
    print(json.dumps(check_installed(wheel=args.wheel),indent=2))
