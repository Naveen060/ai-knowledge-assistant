import io
import re
from pypdf import PdfReader

def chunk_sections(sections, size=900, overlap=150):
    result = []
    total = 0
    for text, locator in sections:
        text = text.strip()
        total += len(text)
        if total > 200000:
            raise ValueError('Extracted text exceeds 200,000 characters')
        for start in range(0, len(text), size-overlap):
            chunk = text[start:start+size].strip()
            if chunk:
                result.append({'text':chunk,'locator':locator})
    if not result:
        raise ValueError('No text found. Scanned PDFs require OCR before upload.')
    return result

def parse_file(name, content):
    if name.lower().endswith('.pdf'):
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError('Use an unencrypted PDF with at most 100 pages')
        return chunk_sections(((page.extract_text() or '',f'page {i+1}') for i,page in enumerate(reader.pages)))
    if name.lower().endswith(('.txt','.md')):
        return chunk_sections([(content.decode('utf-8'), 'text')])
    raise ValueError('Supported files: PDF, UTF-8 TXT and Markdown')

def youtube_chunks(video_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Provide an 11-character YouTube video ID')
    from youtube_transcript_api import YouTubeTranscriptApi
    transcript = YouTubeTranscriptApi().fetch(video_id)
    # Group adjacent transcript segments to preserve enough context per chunk.
    groups, parts, start = [], [], 0
    for snippet in transcript:
        if not parts:
            start = snippet.start
        parts.append(snippet.text)
        if len(' '.join(parts)) >= 750:
            groups.append((' '.join(parts),f'https://www.youtube.com/watch?v={video_id}&t={int(start)}s'))
            parts = []
    if parts:
        groups.append((' '.join(parts),f'https://www.youtube.com/watch?v={video_id}&t={int(start)}s'))
    return chunk_sections(groups)
