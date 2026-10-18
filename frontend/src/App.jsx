import {useState} from 'react';

export default function App(){
  const [token,setToken]=useState(''), [documents,setDocuments]=useState([]), [connected,setConnected]=useState(false);
  const [question,setQuestion]=useState(''),[video,setVideo]=useState(''),[result,setResult]=useState(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState('');
  async function request(path,options={}){
    const response=await fetch('/api'+path,{...options,headers:{Authorization:'Bearer '+token,...options.headers}});
    if(!response.ok){const body=await response.json().catch(()=>({}));throw Error(typeof body.detail==='string'?body.detail:'Request failed. Check your input and connection.');}
    return response.status===204?null:response.json();
  }
  async function run(action){setBusy(true);setError('');setStatus('');try{await action();}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function refresh(){setDocuments(await request('/documents'));}
  async function upload(event){const file=event.target.files[0];if(!file)return;await run(async()=>{const data=new FormData();data.append('file',file);const saved=await request('/documents',{method:'POST',body:data});await refresh();setStatus(`Added ${saved.name} · ${saved.chunks} chunks`);});event.target.value='';}
  function disconnect(){setConnected(false);setToken('');setDocuments([]);setResult(null);setQuestion('');setError('');setStatus('');}
  return <div className="shell"><nav><div className="brand"><span className="mark">K</span>Knowledge Studio</div><span className="badge">Your sources. Clear answers.</span></nav>
    <header className="hero"><div className="eyebrow">AI KNOWLEDGE ASSISTANT</div><h1>A conversation with<br/>everything you know.</h1><p>Bring your documents and videos together. Ask a question. Follow the evidence.</p></header>
    {error&&<div role="alert" className="error">{error}</div>}
    <div className="grid"><aside><section className="card"><h2>Your workspace</h2><p className="muted">Enter your personal access token. It stays in memory for this session.</p>
      {!connected?<form onSubmit={e=>{e.preventDefault();run(async()=>{await refresh();setConnected(true);});}}><label htmlFor="token">Access token</label><input id="token" type="password" value={token} onChange={e=>setToken(e.target.value)} required autoComplete="off"/><button className="full" disabled={busy}>Connect workspace</button></form>:<button className="secondary" onClick={disconnect} disabled={busy}>Disconnect</button>}
    </section>{connected&&<><section className="card"><h2>Add knowledge</h2><label htmlFor="upload">PDF, text or Markdown · up to 10 MB</label><input id="upload" type="file" accept=".pdf,.txt,.md" onChange={upload} disabled={busy}/>
      <form onSubmit={e=>{e.preventDefault();run(async()=>{await request('/youtube',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({video_id:video})});await refresh();setVideo('');setStatus('Video transcript added.');});}}><label htmlFor="video">YouTube video ID</label><input id="video" placeholder="11-character video ID" value={video} onChange={e=>setVideo(e.target.value)} pattern="[A-Za-z0-9_-]{11}" required/><button className="secondary full" disabled={busy}>Import transcript</button></form>
      {status&&<p role="status" className="status">{status}</p>}</section><section className="card"><h2>Library <span className="muted">{documents.length}</span></h2>{documents.length===0?<p className="muted">Your first source belongs here.</p>:documents.map(d=><div className="document" key={d.id}><span>{d.name}</span><button className="danger" aria-label={'Delete '+d.name} disabled={busy} onClick={()=>run(async()=>{await request('/documents/'+d.id,{method:'DELETE'});await refresh();setResult(null);})}>×</button></div>)}</section></>}</aside>
      <main className="card"><h2>Ask your sources</h2><p className="muted">Answers include references so you can check the original context.</p><form onSubmit={e=>{e.preventDefault();run(async()=>setResult(await request('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})})));}}><label htmlFor="question">What would you like to understand?</label><textarea id="question" rows="4" placeholder="What are the key takeaways from my documents?" value={question} onChange={e=>setQuestion(e.target.value)} minLength={3} maxLength={2000} required disabled={!connected}/><button className="full" disabled={busy||!connected}>{busy?'Working…':'Find an answer ↗'}</button></form>
      {result?<><div className="notice">{result.mode||'No matching evidence'} · Always check the cited text.</div><div className="answer">{result.answer}</div>{result.sources.length>0&&<h3>Supporting sources</h3>}{result.sources.map(s=><article className="source" key={s.id}><strong>[{s.citation}] {s.name}</strong><p>{s.locator.startsWith('https://www.youtube.com/')?<a href={s.locator} target="_blank" rel="noreferrer">Open video at timestamp ↗</a>:s.locator}</p><p>{s.text}</p></article>)}</>:<div className="empty"><div className="symbol">✳</div><h3>Good answers start with good sources.</h3><p>Add a document to begin exploring.</p></div>}</main></div>
    <footer>Knowledge Studio · Private document retrieval · PDF / Text / YouTube</footer></div>;
}
