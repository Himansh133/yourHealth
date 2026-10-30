"""Development-only long-document retrieval probe; no DB or paid LLM calls.

Uses installed production embedding/reranking models. This isolates dense retrieval
and reranking, not PostgreSQL full-text fusion or end-to-end answer accuracy.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from app.services.chat.chunking import CHUNKER_VERSION, chunk_pages
from app.services.chat.embeddings import get_embedder, get_reranker
from eval.runners.rechunk import window


def corpus():
    documents, questions = [], []
    # Similar episodes in one synthetic patient's record. Gold is a complete exact
    # sentence in its source document, not a keyword shared by distractors.
    for visit, diet, followup in [
        ('April', 'Avoid added salt and packaged soups.', 'Return to cardiology on Monday.'),
        ('July', 'Avoid sweetened drinks and desserts.', 'Return to endocrinology on Thursday.'),
        ('October', 'Avoid organ meats and alcohol.', 'Return to rheumatology on Friday.'),
    ]:
        background = (f'During the {visit} admission the team reviewed earlier dietary advice and follow-up plans. '
                      'The nursing record describes observations, family discussions and routine monitoring. ')
        # Evidence late in a section, with related but explicitly historical advice nearby.
        text = (f'DISCHARGE SUMMARY: {visit}\nCourse in Hospital\n' + background * 24
                + '\nAdvice on Discharge:\n' + background * 12
                + f'\nCurrent {visit} discharge diet: {diet}\n'
                + f'Current {visit} follow-up: {followup}\n' + background * 8)
        documents.append((visit, [(1, text)]))
        questions.extend([
            {'id': f'{visit}-diet', 'document': visit, 'question': f'What food should be avoided after the {visit} admission?',
             'gold': f'Current {visit} discharge diet: {diet}'},
            {'id': f'{visit}-followup', 'document': visit, 'question': f'Which clinic and day were specified after the {visit} admission?',
             'gold': f'Current {visit} follow-up: {followup}'},
        ])
    return documents, questions


def reciprocal_rank(order, relevant):
    return next((1 / rank for rank, index in enumerate(order, 1) if index in relevant), 0.0)


def run(embedder, reranker, sizes=(190, 300, 450)):
    documents, questions = corpus()
    query_vectors = np.asarray(embedder.embed([q['question'] for q in questions]))
    results = []
    for size in sizes:
        with window(size):
            chunks = [(name, c) for name, pages in documents for c in chunk_pages(pages, 'discharge')]
        vectors = np.asarray(embedder.embed([c.text for _, c in chunks]))
        for q, vector in zip(questions, query_vectors):
            relevant = {i for i, (name, c) in enumerate(chunks) if name == q['document'] and q['gold'] in c.text}
            if not relevant:
                raise ValueError(f"No intact gold evidence at size {size}: {q['id']}")
            dense = np.argsort(-(vectors @ vector), kind='stable').tolist()
            candidates = dense[:10]
            scores = reranker.score(q['question'], [chunks[i][1].text for i in candidates])
            reranked = [i for _, i in sorted(zip(scores, candidates), key=lambda pair: -pair[0])]
            for system, order in [('dense', dense), ('dense+reranker', reranked)]:
                results.append({'words': size, 'question': q['id'], 'system': system,
                                'chunks': len(chunks), 'mrr': reciprocal_rank(order, relevant),
                                **{f'recall@{k}': int(bool(set(order[:k]) & relevant)) for k in (1, 3, 6, 10)}})
        print(f'Completed {size}-word retrieval probe', flush=True)
    return results


def main(out):
    embedder, reranker = get_embedder(), get_reranker()
    if embedder is None or reranker is None:
        raise SystemExit('Installed embedding and reranker models are required; no silent keyword fallback.')
    from app.core.config import settings
    rows = run(embedder, reranker)
    artifact = {'scope': 'development diagnostic; dense retrieval only, no full-text fusion or answer generation',
                'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'source_sha256': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in
                    ('app/services/chat/chunking.py', '../eval/runners/retrieval_challenge.py')},
                'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
                'chunker': CHUNKER_VERSION, 'embedder': embedder.name, 'reranker': settings.reranker_model,
                'corpus_sha256': hashlib.sha256(json.dumps(corpus(), sort_keys=True).encode()).hexdigest(),
                'results': rows}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + '\n')
    lines = ['# Long-document retrieval development probe', '', artifact['scope'], '',
             '| Words | System | MRR | Recall@1 | Recall@3 | Recall@6 | Recall@10 |',
             '|---|---|---|---|---|---|---|']
    for size in (190, 300, 450):
        for system in ('dense', 'dense+reranker'):
            group = [r for r in rows if r['words'] == size and r['system'] == system]
            vals = [sum(r[m] for r in group) / len(group) for m in ('mrr', 'recall@1', 'recall@3', 'recall@6', 'recall@10')]
            lines.append(f'| {size} | {system} | ' + ' | '.join(f'{v:.3f}' for v in vals) + ' |')
    lines += ['', 'Six synthetic questions over three similar long discharge notes. This small development probe',
              'does not establish a general reranker benefit or replace the frozen 90-question test.']
    out.with_suffix('.md').write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    main(ap.parse_args().out)
