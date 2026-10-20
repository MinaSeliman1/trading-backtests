from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import os
import uuid
import pytest
from qqq_paper.windows_vault import WindowsVault,CredentialError,validate_credentials


def test_credentials_validation_never_echoes_values():
    for value in [('', 'x'),('private-key\n','private-secret'),('x',None)]:
        with pytest.raises(CredentialError) as error:validate_credentials(*value)
        assert 'private-key' not in str(error.value) and 'private-secret' not in str(error.value)


@pytest.mark.skipif(os.name!='nt',reason='Windows Credential Manager integration')
def test_actual_windows_vault_roundtrip_and_delete_only_unique_test_target():
    vault=WindowsVault('TradingBacktests.Tests/'+uuid.uuid4().hex)
    try:
        vault.save('test-paper-id','test-paper-secret')
        assert vault.load()==('test-paper-id','test-paper-secret')
        assert 'test-paper-secret' not in repr(vault)
    finally:vault.delete()
    with pytest.raises(CredentialError):vault.load()
