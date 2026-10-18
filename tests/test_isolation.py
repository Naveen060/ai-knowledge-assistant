import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ingest import parse_file, chunk_sections

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('USER_TOKENS',json.dumps({'alice-secret':'alice','bob-secret':'bob'}))
    monkeypatch.setenv('STORE_PATH',str(tmp_path/'knowledge.db'))
    monkeypatch.setenv('EMBEDDING_BACKEND','hash')
    monkeypatch.setenv('GENERATION_BACKEND','extractive')
    with TestClient(app) as client:
        yield client

def headers(token):
    return {'Authorization':'Bearer '+token}

def test_tenant_isolation_and_delete(client):
    alice, bob = headers('alice-secret'), headers('bob-secret')
    response = client.post('/api/documents',headers=alice,files={'file':('policy.txt',b'Acme vacation policy grants twenty days paid leave to employees.','text/plain')})
    assert response.status_code == 201, response.text
    identifier = response.json()['id']
    assert client.get('/api/documents',headers=bob).json() == []
    assert client.delete('/api/documents/'+identifier,headers=bob).status_code == 404
    assert client.post('/api/ask',headers=bob,json={'question':'vacation policy'}).json()['sources'] == []
    response = client.post('/api/ask',headers=alice,json={'question':'vacation policy'})
    assert 'twenty' in response.json()['answer']
    assert response.json()['sources'][0]['name'] == 'policy.txt'
    assert client.delete('/api/documents/'+identifier,headers=alice).status_code == 204
    assert client.post('/api/ask',headers=alice,json={'question':'vacation policy'}).json()['sources'] == []

def test_bad_auth_and_inputs(client):
    assert client.get('/api/documents').status_code == 401
    assert client.get('/api/documents',headers=headers('fake')).status_code == 401
    assert client.post('/api/youtube',headers=headers('alice-secret'),json={'video_id':'http://localhost'}).status_code == 422
    assert client.post('/api/documents',headers=headers('alice-secret'),files={'file':('bad.txt',b'')}).status_code == 422

def test_chunk_bounds():
    with pytest.raises(ValueError):
        chunk_sections([('a'*200001,'text')])
    chunks = parse_file('readme.md',b'Hello '*300)
    assert len(chunks) > 1
    assert all(len(c['text']) <= 900 for c in chunks)

def test_persistence(tmp_path):
    from app.store import Store
    from app.retrieval import Retriever
    import os
    os.environ['EMBEDDING_BACKEND']='hash'
    store = Store(tmp_path/'persist.db')
    engine = Retriever()
    chunks = [{'text':'Long term knowledge persists across server restarts.','locator':'text'}]
    store.add('alice','memo',chunks,engine.embed([chunks[0]['text']]),engine.signature)
    assert len(Store(tmp_path/'persist.db').chunks('alice')) == 1
