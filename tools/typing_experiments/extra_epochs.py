#!/usr/bin/env python3
"""Continue shipped REC2 weights; freeze one selection using verified dev only.

Training needs MLX; evaluate-dev needs the existing CatBoost host environment.
Neither command parses test data. Dev verification hashes the frozen aggregate
export solely for receipt integrity; those bytes never enter model fitting/scoring.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import neural_refinement as neural

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'build/typing-refinement/data'
OBSERVATIONS = ROOT / 'build/typing-refinement/verified-observations/dev.jsonl'
ASSETS = ROOT / 'app/src/main/assets/smarttyping/experiments'
OUT = ROOT / 'build/typing-extra-epochs/training'
MANIFEST_SHA256 = '20b32e840b890aab726fabea30c6409fce058d0c9ba3dd64d603aaaa24475ce7'
EPOCHS = 12
CHECKPOINTS = (2, 4, 8, 12)
SEED = 16092026
BATCH_SIZE = 1024
LEARNING_RATE = .0005
DECAY = .9


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n')


def require_hash(path, expected):
    if sha(path) != expected:
        raise ValueError('INPUT_IDENTITY: '+str(path))


def verified_inputs(data=DATA):
    require_hash(data/'manifest.json', MANIFEST_SHA256)
    manifest = json.loads((data/'manifest.json').read_text())
    if manifest.get('containsPersonalMessages') is not False:
        raise ValueError('PUBLIC_DATA_REQUIRED')
    source = json.loads((ROOT/'tools/model/rune-text-0.2/source-lock.json').read_text())
    if manifest['sourceSha256'] != source['wikipediaContext']['files']['ru-0007.parquet']['sha256']:
        raise ValueError('PUBLIC_SOURCE_IDENTITY')
    train = neural.verified_text(data, 'train', manifest)
    dev = neural.verified_text(data, 'dev', manifest)
    if not train or not dev or {r['articleId'] for r in train} & {r['articleId'] for r in dev}:
        raise ValueError('TRAIN_DEV_PARTITIONS')
    for name, rows in [('train', train), ('dev', dev)]:
        if sum(len(r['text']) for r in rows) != manifest['partitions'][name]['characters']:
            raise ValueError('CHARACTER_COUNT')
    return manifest, train, dev


def verified_dev(path=OBSERVATIONS):
    """Reuse full receipt validation; aggregate exports are hash-only inputs."""
    if Path(path).resolve() != OBSERVATIONS.resolve():
        raise ValueError('DEV_ONLY')
    import rank_refinement as rank
    return rank.verified_groups(path, 'dev')


def plan_inputs():
    # Hash only train/dev payloads and immutable provenance, never aggregate rows.
    paths = [DATA/'manifest.json', DATA/'train-text.jsonl', DATA/'dev-text.jsonl',
             DATA/'dev-rows.jsonl', OBSERVATIONS, OBSERVATIONS.parent/'manifest.json',
             ASSETS/'ru-ranking-context.bin', ASSETS/'ru-ranker.bin', Path(__file__),
             Path(neural.__file__), Path(__file__).with_name('rank_refinement.py'),
             Path(__file__).with_name('train.py'), ROOT/'tools/model/rune-text-0.2/source-lock.json']
    binding = json.loads((OBSERVATIONS.parent/'manifest.json').read_text())
    paths.append(Path(binding['exportReceipt']))
    return {str(p.resolve()): sha(p) for p in paths}


def original_copy(source, destination):
    original = neural.load_model(source)
    if (original.window, original.hidden) != (48, 48):
        raise ValueError('REC2_REQUIRED')
    decoded = neural.export_model(original, destination)
    if Path(source).read_bytes() != Path(destination).read_bytes():
        raise ValueError('INITIAL_WEIGHTS_CHANGED')
    return decoded


def choose(models):
    if 'original' not in models:
        raise ValueError('ORIGINAL_CANDIDATE_REQUIRED')
    if any(not np.isfinite(m['devCE']) or m['combinedTop1'] < 0 for m in models.values()):
        raise ValueError('INVALID_SELECTION_METRICS')
    return min(models, key=lambda name: (-models[name]['combinedTop1'], models[name]['devCE'], name != 'original', name))


def learning_rate(epoch):
    if not 1 <= epoch <= EPOCHS:
        raise ValueError('EXTRA_EPOCH_BOUNDS')
    return LEARNING_RATE * DECAY**(epoch-1)


def train():
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    manifest, train_rows, dev_rows = verified_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'plan.json').exists():
        raise ValueError('TRAINING_ALREADY_FROZEN')
    plan = {'schema': 1, 'seed': SEED, 'additionalEpochs': EPOCHS, 'checkpoints': list(CHECKPOINTS),
            'batchSize': BATCH_SIZE, 'learningRate': LEARNING_RATE, 'epochDecay': DECAY,
            'optimizer': 'Adam bias_correction=True; state reset (prior state unavailable)',
            'initialModel': str(ASSETS/'ru-ranking-context.bin'), 'dimensions': [48, 48],
            'selection': 'combined top1; lower dev character CE; exact tied original; then name',
            'originalIncluded': True, 'endOfWord': True, 'blendGain': 1,
            'testAccess': False, 'aggregateExportAccess': 'hash-only receipt integrity during dev verification; no test parsing', 'inputs': plan_inputs(), 'python': sys.version,
            'numpy': np.__version__, 'mlx': __import__('importlib.metadata', fromlist=['version']).version('mlx'),
            'createdUnix': time.time(), 'trainCharacters': manifest['partitions']['train']['characters'],
            'devCharacters': manifest['partitions']['dev']['characters']}
    write(OUT/'plan.json', plan)
    original = original_copy(ASSETS/'ru-ranking-context.bin', OUT/'original.bin')
    x, y = neural.samples(train_rows, 48)
    dx, dy = neural.samples(dev_rows, 48)
    class Network(nn.Module):
        def __init__(self):
            super().__init__()
            for key, value in zip(('w1', 'b1', 'w2', 'b2'), original.weights):
                setattr(self, key, mx.array(value))
        def __call__(self, xx):
            h = mx.tanh(self.w1[xx+mx.arange(48)*34].sum(axis=1)+self.b1)
            return h@self.w2+self.b2
    net = Network()
    # Prove the actual MLX initialization survives export without changing a bit.
    initial = neural.Model(48, 48, [np.array(net[k]) for k in ('w1','b1','w2','b2')])
    neural.export_model(initial, OUT/'mlx-initial.bin')
    require_hash(OUT/'mlx-initial.bin', sha(OUT/'original.bin'))
    rng = np.random.default_rng(SEED)
    optimizer = optim.Adam(learning_rate=LEARNING_RATE, bias_correction=True)
    loss_grad = nn.value_and_grad(net, lambda m, xx, yy: nn.losses.cross_entropy(m(xx), yy, reduction='mean'))
    metrics = {'planSha256': sha(OUT/'plan.json'), 'epochs': [], 'models': {}}
    def record(name, model, epoch):
        path = OUT/(name+'.bin')
        decoded = neural.export_model(model, path)
        item = {'additionalEpochs': epoch, 'devCE': neural.cross_entropy(decoded, dx, dy),
                'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}
        metrics['models'][name] = item
        write(OUT/'metrics.json', metrics)
        print('checkpoint', name, json.dumps(item), flush=True)
    record('original', original, 0)
    for epoch in range(1, EPOCHS+1):
        optimizer.learning_rate = learning_rate(epoch)
        order = rng.permutation(len(y))
        total = 0.0
        for start in range(0, len(y), BATCH_SIZE):
            batch = order[start:start+BATCH_SIZE]
            loss, grad = loss_grad(net, mx.array(x[batch]), mx.array(y[batch]))
            optimizer.update(net, grad)
            mx.eval(net.parameters(), optimizer.state, loss)
            total += float(loss.item())*len(batch)
        item = {'epoch': epoch, 'trainCE': total/len(y), 'learningRate': learning_rate(epoch)}
        metrics['epochs'].append(item)
        write(OUT/'metrics.json', metrics)
        print('epoch', json.dumps(item), flush=True)
        if epoch in CHECKPOINTS:
            record('extra-'+str(epoch), neural.Model(48,48,[np.array(net[k]) for k in ('w1','b1','w2','b2')]), epoch)
    metrics['complete'] = True
    write(OUT/'metrics.json', metrics)


def evaluate_dev():
    import rank_refinement as rank
    if (OUT/'selection.json').exists():
        raise ValueError('SELECTION_ALREADY_FROZEN')
    plan = json.loads((OUT/'plan.json').read_text())
    for path, digest in plan['inputs'].items():
        require_hash(path, digest)
    metrics = json.loads((OUT/'metrics.json').read_text())
    require_hash(OUT/'plan.json', metrics['planSha256'])
    if not metrics.get('complete') or set(metrics['models']) != {'original', 'extra-2', 'extra-4', 'extra-8', 'extra-12'}:
        raise ValueError('INCOMPLETE_CHECKPOINT_SET')
    groups = verified_dev()
    trees = rank.scores(ASSETS/'ru-ranker.bin', groups)
    report = {'models': {}, 'rowsWithAlternatives': len(groups), 'allRows': json.loads((DATA/'manifest.json').read_text())['partitions']['dev']['rows'],
              'expectedAvailable': sum(int(y.sum()>0) for _,_,y in groups)}
    scores = {'rowIds': [r['id'] for r,_,_ in groups], 'tree': trees,
              'candidates': [[c['text'] for c in cs] for _,cs,_ in groups], 'neural': {}, 'combined': {}}
    for name, item in metrics['models'].items():
        require_hash(item['path'], item['sha256'])
        model = neural.load_model(item['path'])
        context = [[neural.context_score(model,r['prefix'],c['text']) for c in cs] for r,cs,_ in groups]
        combined = [(np.asarray(a)+b).tolist() for a,b in zip(trees, context)]
        scores['neural'][name] = context
        scores['combined'][name] = combined
        report['models'][name] = dict(item, combinedTop1=rank.accuracy(groups, combined), neuralTop1=rank.accuracy(groups, context))
        print(name, json.dumps(report['models'][name]), flush=True)
    selected = choose(report['models'])
    write(OUT/'dev-scores.json', scores)
    write(OUT/'dev-report.json', report)
    write(OUT/'selection.json', {'selected': selected, 'selectedPath': report['models'][selected]['path'],
          'selectedSha256': report['models'][selected]['sha256'], 'planSha256': sha(OUT/'plan.json'),
          'metricsSha256': sha(OUT/'metrics.json'), 'devReportSha256': sha(OUT/'dev-report.json'),
          'devScoresSha256': sha(OUT/'dev-scores.json'), 'observationsSha256': sha(OBSERVATIONS),
          'rankerSha256': sha(ASSETS/'ru-ranker.bin'), 'originalSha256': report['models']['original']['sha256'],
          'devTop1Before': report['models']['original']['combinedTop1'], 'devTop1After': report['models'][selected]['combinedTop1'],
          'selectionFrozenBeforeTest': True,
          'testAccess': False, 'devImproved': report['models'][selected]['combinedTop1'] > report['models']['original']['combinedTop1']})
    print('selected', selected, report['models'][selected]['sha256'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('train', 'evaluate-dev'))
    args = parser.parse_args()
    {'train': train, 'evaluate-dev': evaluate_dev}[args.command]()
