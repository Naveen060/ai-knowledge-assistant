import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.auth import current_user
from app.store import Store
from app.retrieval import Retriever
from app.ingest import parse_file, youtube_chunks
from app.generation import answer

load_dotenv()
log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    app.state.store = Store(os.getenv('STORE_PATH','data/knowledge.db'))
    app.state.retriever = Retriever()
    yield

app = FastAPI(title='AI Knowledge Assistant', lifespan=lifespan)

class Question(BaseModel):
    question: str = Field(min_length=3,max_length=2000)

class Video(BaseModel):
    video_id: str = Field(pattern=r'^[A-Za-z0-9_-]{11}$')

def save(user, name, chunks):
    vectors = app.state.retriever.embed([c['text'] for c in chunks])
    identifier = app.state.store.add(user,name,chunks,vectors,app.state.retriever.signature)
    return {'id':identifier,'name':name,'chunks':len(chunks)}

@app.get('/api/health')
def health():
    return {'status':'ok'}

@app.get('/api/documents')
def documents(user=Depends(current_user)):
    return app.state.store.documents(user)

@app.post('/api/documents', status_code=201)
def ingest(file: UploadFile = File(...), user=Depends(current_user)):
    content = file.file.read(10*1024*1024+1)
    if len(content) > 10*1024*1024:
        raise HTTPException(413,'File exceeds 10 MB')
    try:
        return save(user,(file.filename or 'document')[:200],parse_file(file.filename or '',content))
    except Exception as exc:
        log.info('Ingestion failed: %s', type(exc).__name__)
        raise HTTPException(422,'Could not ingest this document; use readable PDF or UTF-8 text within quota') from exc

@app.post('/api/youtube', status_code=201)
def youtube(body: Video, user=Depends(current_user)):
    try:
        return save(user,'YouTube '+body.video_id,youtube_chunks(body.video_id))
    except Exception as exc:
        log.info('Transcript ingestion failed: %s', type(exc).__name__)
        raise HTTPException(422,'Transcript unavailable or exceeds ingestion quota') from exc

@app.delete('/api/documents/{document_id}', status_code=204)
def delete(document_id: str, user=Depends(current_user)):
    if not app.state.store.delete(user,document_id):
        raise HTTPException(404,'Document not found')

@app.post('/api/ask')
def ask(body: Question, user=Depends(current_user)):
    try:
        sources = app.state.retriever.search(body.question,app.state.store.chunks(user))
        return answer(body.question,sources)
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc
    except Exception as exc:
        log.exception('Answer provider failed')
        raise HTTPException(502,'Answer provider unavailable') from exc

if Path('frontend/dist').exists():
    app.mount('/',StaticFiles(directory='frontend/dist',html=True),name='frontend')
