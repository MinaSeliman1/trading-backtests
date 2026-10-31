"""Safe process-exit evidence. No messages, source lines, locals, keys or network."""
from pathlib import Path
from datetime import datetime,timezone
import os,json,traceback
_reported=False

def _write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
    temp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)

def _number(error,name):
    try:value=getattr(error,name,None)
    except Exception:return None
    return value if isinstance(value,int) else None

def record_failure(runtime,component,error=None,exit_code=1):
    global _reported
    if component not in ('noise','orb'):return False
    _reported=True
    try:
        frames=[]
        if error is not None:
            for frame,line in traceback.walk_tb(error.__traceback__):
                frames.append(dict(file=Path(frame.f_code.co_filename).name,line=line,function=frame.f_code.co_name))
        value=dict(utc=datetime.now(timezone.utc).isoformat(),pid=os.getpid(),component=component,exit_code=exit_code if isinstance(exit_code,int) else 1,
            error_type=type(error).__name__ if error is not None else 'ExplicitExit',errno=_number(error,'errno'),winerror=_number(error,'winerror'),frames=frames[-12:],
            messages_and_locals_omitted=True)
        paths=[Path(runtime)/'windows/last_fatal.json']
        local=os.environ.get('LOCALAPPDATA')
        if local:paths.append(Path(local)/'TradingBacktests/Diagnostics'/component/'last_fatal.json')
        for path in paths:
            try:_write(path,value);return True
            except Exception:pass
    except Exception:pass
    return False

def run(entry,runtime,component):
    global _reported
    _reported=False
    try:
        result=entry();code=0 if result is None else result if isinstance(result,int) else 1
    except SystemExit as error:
        code=0 if error.code is None else error.code if isinstance(error.code,int) else 1
        if code:record_failure(runtime,component,error,code)
        return code
    except Exception as error:
        record_failure(runtime,component,error,1);return 1
    if code and not _reported:record_failure(runtime,component,exit_code=code)
    return code

def runtime_from_args(arguments,default):
    result=Path(default)
    for index,value in enumerate(arguments):
        if value=='--runtime' and index+1<len(arguments):result=Path(arguments[index+1])
        elif value.startswith('--runtime='):result=Path(value.split('=',1)[1])
    return result
