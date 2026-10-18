import json
import os
import re
import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import HashingVectorizer

def tokenize(text):
    return re.findall(r'\w+', text.lower()) or ['_empty_']

class Retriever:
    def __init__(self):
        self.semantic = os.getenv('EMBEDDING_BACKEND','hash') == 'sentence-transformers'
        model = os.getenv('EMBEDDING_MODEL','sentence-transformers/all-MiniLM-L6-v2')
        self.signature = model if self.semantic else 'hash-384-v1'
        if self.semantic:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer(model)
        else:
            self.encoder = HashingVectorizer(n_features=384, alternate_sign=False, norm='l2')

    def embed(self, texts):
        if self.semantic:
            return np.asarray(self.encoder.encode(texts, normalize_embeddings=True), dtype='float32')
        return self.encoder.transform(texts).toarray().astype('float32')

    def search(self, question, chunks, k=5):
        if not chunks:
            return []
        if any(c['model'] != self.signature for c in chunks):
            raise ValueError('Embedding model changed: delete and re-ingest existing documents')
        matrix = np.asarray([json.loads(c['embedding']) for c in chunks], dtype='float32')
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        depth = min(20, len(chunks))
        similarities, ids = index.search(self.embed([question]), depth)
        lexical = BM25Okapi([tokenize(c['text']) for c in chunks]).get_scores(tokenize(question))
        # Reciprocal rank fusion avoids comparing incompatible cosine and BM25 scales.
        scores = {}
        for rank, (idx, similarity) in enumerate(zip(ids[0], similarities[0])):
            if idx >= 0 and similarity > 0.05:
                scores[int(idx)] = scores.get(int(idx),0) + 1/(60+rank+1)
        for rank, idx in enumerate(np.argsort(-lexical)[:depth]):
            if lexical[idx] > 0:
                scores[int(idx)] = scores.get(int(idx),0) + 1/(60+rank+1)
        selected = sorted(scores, key=scores.get, reverse=True)[:k]
        return [{key:chunks[i][key] for key in ('id','document_id','name','text','locator')} |
                {'score':scores[i]} for i in selected]
