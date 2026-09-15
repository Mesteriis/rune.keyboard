#!/usr/bin/env python3
"""Frozen candidate-level REC2 training; only verified train/dev labels are read.

Prepare runs in the CatBoost host environment; train requires MLX; evaluate-dev
requires NumPy only. Aggregate candidate exports are hashed solely for integrity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import neural_refinement as neural

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'build/typing-word-ranking/training'
ASSETS = ROOT / 'app/src/main/assets/smarttyping/experiments'
OBS = ROOT / 'build/typing-word-ranking/observations'
OLD = ROOT / 'build/typing-refinement/verified-observations'
PLAN = ROOT / 'docs/superpowers/plans/2026-09-15-word-ranking.md'
KEYS = ('w1', 'b1', 'w2', 'b2')
SEED = 17092026
EPOCHS = 6
CHECKPOINTS = (1, 2, 4, 6)
BATCH_SIZE = 16
TEMPERATURE = .1
DISTILLATION = .1


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                   sort_keys=True, allow_nan=False)+'\n')


def require_hash(path, digest):
    if sha(path) != digest:
        raise ValueError('INPUT_IDENTITY: '+str(path))


def verified_records(path, partition):
    path = Path(path).resolve()
    if partition not in ('train', 'dev') or path.name != partition+'.jsonl':
        raise ValueError('TRAIN_DEV_ONLY')
    import rank_refinement as rank
    rank.verified_groups(path, partition)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if any(item['row']['partition'] != partition for item in records):
        raise ValueError('PARTITION_ALIGNMENT')
    return records


def is_typo(row):
    return row.get('cohort') == 'typo' and not row.get('noAuto', False) and row.get('errorCount', 1) > 0


def encode(context, candidate):
    """Current scorer's causal 48-character history, 32-character word + space."""
    if not candidate or len(candidate) > 128:
        raise ValueError('UNSUPPORTED_CANDIDATE')
    history = context[-48:].lower()
    if history and not history[-1].isspace():
        history += ' '
    word = candidate[:32].lower()+' '
    xs = []
    for char in word:
        xs.append(([0]*48+neural.ids(history[-48:]))[-48:])
        history = (history+char)[-48:]
    return np.array(xs, dtype=np.int32), np.array(neural.ids(word), dtype=np.int32)


def pack(records, trees):
    """JSON-compatible train/dev cache; no future text or test rows are retained."""
    groups = []
    coverage = {}
    for record, tree in zip(records, trees, strict=True):
        row, generation = record['row'], record['observation']['generation']
        candidates = generation['alternatives']
        expected = row.get('expectedSpelling', '').lower()
        labels = [int(bool(expected) and c['text'].lower() == expected) for c in candidates]
        typo = is_typo(row)
        eligible = typo and len(candidates) >= 2 and 0 < sum(labels) < len(labels)
        key = str(row.get('errorCount', 1)) if typo else 'control'
        bucket = coverage.setdefault(key, dict(rows=0, withAlternatives=0, expectedAvailable=0, eligible=0))
        bucket['rows'] += 1
        bucket['withAlternatives'] += bool(candidates)
        bucket['expectedAvailable'] += int(any(labels))
        bucket['eligible'] += int(eligible)
        groups.append(dict(id=row['id'], articleId=row['articleId'], prefix=row['prefix'],
                           candidates=[c['text'] for c in candidates], labels=labels, tree=tree,
                           typo=typo, editCount=row.get('errorCount', 1), eligible=eligible))
    return groups, coverage


def prepare():
    import rank_refinement as rank
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'plan.json').exists():
        raise ValueError('ALREADY_FROZEN')
    records = {name: verified_records(directory/(split+'.jsonl'), split)
               for name, directory, split in [('newTrain', OBS, 'train'), ('oldTrain', OLD, 'train'),
                                               ('newDev', OBS, 'dev'), ('oldDev', OLD, 'dev')]}
    train_articles = {r['row']['articleId'] for key in ('newTrain', 'oldTrain') for r in records[key]}
    dev_articles = {r['row']['articleId'] for key in ('newDev', 'oldDev') for r in records[key]}
    if train_articles & dev_articles:
        raise ValueError('TRAIN_DEV_ARTICLE_OVERLAP')
    frozen = [PLAN, Path(__file__), Path(__file__).with_name('test_word_ranking.py'),
              Path(neural.__file__), Path(rank.__file__), Path(rank.baseline.__file__),
              ROOT/'tools/model/rune-text-0.2/source-lock.json',
              ASSETS/'ru-ranking-context.bin', ASSETS/'ru-ranker.bin']
    for directory in (OBS, OLD):
        frozen += [directory/'train.jsonl', directory/'dev.jsonl', directory/'manifest.json']
        binding = json.loads((directory/'manifest.json').read_text())
        frozen += [Path(binding['dataManifest']), Path(binding['exportReceipt'])]
    original = neural.load_model(ASSETS/'ru-ranking-context.bin')
    if (original.window, original.hidden) != (48, 48) or (ASSETS/'ru-ranker.bin').read_bytes()[:4] != b'RET2':
        raise ValueError('SHIPPED_REC2_RET2_REQUIRED')
    neural.export_model(original, OUT/'original.bin')
    require_hash(OUT/'original.bin', sha(ASSETS/'ru-ranking-context.bin'))
    data, coverage = {}, {}
    for name, items in records.items():
        triples = [(r['row'], r['observation']['generation']['alternatives'], None) for r in items]
        trees = rank.scores(ASSETS/'ru-ranker.bin', triples)
        data[name], coverage[name] = pack(items, trees)
        print('prepared', name, json.dumps(coverage[name]), flush=True)
    write(OUT/'prepared.json', data)
    frozen += [OUT/'prepared.json', OUT/'original.bin']
    plan = dict(schemaVersion=1, seed=SEED, epochs=EPOCHS, checkpoints=list(CHECKPOINTS),
                batchGroups=BATCH_SIZE, temperature=TEMPERATURE, distillation=DISTILLATION,
                learningRate=.0001, epochDecay=.9, optimizer='Adam bias_correction=True; state reset',
                dimensions=[48, 48], terminalSpace=True, characterLogProbabilityFloor=1e-9,
                rankingLoss='negative log summed gold mass in group softmax of (fixed tree + exact clamped mean character logP score) / 0.1',
                distillationLoss='KL(original || current), mean over real characters of all candidates per group, then batch mean',
                selection='new typo dev combined top1; old typo dev combined top1; original; earlier epoch',
                testAccess=False, aggregateExportAccess='hash-only integrity; never parsed',
                inputs={str(p.resolve()): sha(p) for p in frozen}, coverage=coverage,
                createdUnix=time.time(), preparationNumpy=np.__version__)
    write(OUT/'plan.json', plan)
    print('freeze', sha(OUT/'plan.json'), flush=True)


def read_frozen():
    plan = json.loads((OUT/'plan.json').read_text())
    if plan['testAccess'] or plan['epochs'] != EPOCHS or plan['checkpoints'] != list(CHECKPOINTS):
        raise ValueError('FROZEN_CONFIGURATION_REQUIRED')
    for path, digest in plan['inputs'].items():
        require_hash(path, digest)
    return plan, json.loads((OUT/'prepared.json').read_text())


def batch_arrays(groups):
    encoded = [[encode(g['prefix'], c) for c in g['candidates']] for g in groups]
    count = max(len(c) for c in encoded)
    length = max(len(y) for cs in encoded for _, y in cs)
    shape = (len(groups), count, length)
    x = np.zeros((*shape, 48), dtype=np.int32)
    y = np.zeros(shape, dtype=np.int32)
    mask = np.zeros(shape, dtype=np.float32)
    tree = np.zeros(shape[:2], dtype=np.float32)
    labels = np.zeros(shape[:2], dtype=np.float32)
    for i, (g, cs) in enumerate(zip(groups, encoded)):
        for j, (xx, yy) in enumerate(cs):
            x[i, j, :len(yy)] = xx
            y[i, j, :len(yy)] = yy
            mask[i, j, :len(yy)] = 1
        tree[i, :len(cs)] = g['tree']
        labels[i, :len(cs)] = g['labels']
    return x, y, mask, tree, labels


def network_class():
    import mlx.core as mx
    import mlx.nn as nn
    class Network(nn.Module):
        def __init__(self, model):
            super().__init__()
            if (model.window, model.hidden) != (48, 48):
                raise ValueError('REC2_REQUIRED')
            for key, value in zip(KEYS, model.weights):
                setattr(self, key, mx.array(value))
        def __call__(self, x):
            h = mx.tanh(self.w1[x+mx.arange(48)*34].sum(axis=-2)+self.b1)
            # MLX GPU matmul may use reduced internal precision; explicit float32
            # multiply/reduce preserves the portable scorer within float32 error.
            return (h[..., None]*self.w2).sum(axis=-2)+self.b2
    return Network


def loss_mlx(net, teacher, x, y, mask, tree, labels):
    import mlx.core as mx
    logp = net(x)
    logp = logp-mx.logsumexp(logp, axis=-1, keepdims=True)
    teacher_logp = mx.stop_gradient(teacher(x))
    teacher_logp = mx.stop_gradient(teacher_logp-mx.logsumexp(teacher_logp, axis=-1, keepdims=True))
    chosen = mx.take_along_axis(logp, y[..., None], axis=-1).squeeze(-1)
    counts = mask.sum(axis=-1)
    score = mx.clip(((mx.maximum(chosen, np.log(1e-9))*mask).sum(axis=-1)/mx.maximum(counts, 1)+3)*.25, -.5, .5)
    ranking = mx.where(counts > 0, (tree+score)/TEMPERATURE, -1e9)
    ce = mx.logsumexp(ranking, axis=-1)-mx.logsumexp(mx.where(labels > 0, ranking, -1e9), axis=-1)
    kl_char = (mx.exp(teacher_logp)*(teacher_logp-logp)).sum(axis=-1)
    kl = (kl_char*mask).sum(axis=(-2, -1))/mask.sum(axis=(-2, -1))
    return (ce+DISTILLATION*kl).mean()


def numpy_loss(model, teacher, arrays):
    x, y, mask, tree, labels = arrays
    shape = y.shape
    def logp(m):
        z = neural.logits(m, x.reshape(-1, 48)).reshape(*shape, 34)
        z -= z.max(axis=-1, keepdims=True)
        return z-np.log(np.exp(z).sum(axis=-1, keepdims=True))
    current, original = logp(model), logp(teacher)
    chosen = np.take_along_axis(current, y[..., None], axis=-1)[..., 0]
    counts = mask.sum(axis=-1)
    scores = np.clip(((np.maximum(chosen, np.log(1e-9))*mask).sum(axis=-1)/np.maximum(counts, 1)+3)*.25, -.5, .5)
    ranking = np.where(counts > 0, (tree+scores)/TEMPERATURE, -1e9)
    z = ranking-ranking.max(axis=-1, keepdims=True)
    ce = np.log(np.exp(z).sum(axis=-1))-np.log((np.exp(z)*labels).sum(axis=-1))
    kl = (np.sum(np.exp(original)*(original-current), axis=-1)*mask).sum(axis=(-2, -1))/mask.sum(axis=(-2, -1))
    return float(np.mean(ce+DISTILLATION*kl))


def train():
    import importlib.metadata
    import mlx.core as mx
    import mlx.nn as nn
    import mlx.optimizers as optim
    _, data = read_frozen()
    if (OUT/'metrics.json').exists():
        raise ValueError('TRAINING_ALREADY_STARTED')
    groups = [g for key in ('newTrain', 'oldTrain') for g in data[key] if g['eligible']]
    if not groups:
        raise ValueError('NO_ELIGIBLE_TRAIN_GROUPS')
    original = neural.load_model(OUT/'original.bin')
    Network = network_class()
    net, teacher = Network(original), Network(original)
    initial = neural.Model(48, 48, [np.array(net[k]) for k in KEYS])
    neural.export_model(initial, OUT/'mlx-initial.bin')
    require_hash(OUT/'mlx-initial.bin', sha(OUT/'original.bin'))
    mx.random.seed(SEED)
    rng = np.random.default_rng(SEED)
    optimizer = optim.Adam(learning_rate=.0001, bias_correction=True)
    loss_grad = nn.value_and_grad(net, lambda m, *args: loss_mlx(m, teacher, *args))
    metrics = dict(planSha256=sha(OUT/'plan.json'), trainGroups=len(groups), epochs=[], models={},
                   numpy=np.__version__, mlx=importlib.metadata.version('mlx'), complete=False)
    def record(name, epoch):
        path = OUT/(name+'.bin')
        neural.export_model(neural.Model(48, 48, [np.array(net[k]) for k in KEYS]), path)
        metrics['models'][name] = dict(epoch=epoch, path=str(path), sha256=sha(path), bytes=path.stat().st_size)
        write(OUT/'metrics.json', metrics)
    record('original', 0)
    for epoch in range(1, EPOCHS+1):
        optimizer.learning_rate = .0001*.9**(epoch-1)
        total, started = 0., time.monotonic()
        order = rng.permutation(len(groups))
        for start in range(0, len(groups), BATCH_SIZE):
            batch = [groups[i] for i in order[start:start+BATCH_SIZE]]
            arrays = [mx.array(a) for a in batch_arrays(batch)]
            loss, grad = loss_grad(net, *arrays)
            optimizer.update(net, grad)
            mx.eval(net.parameters(), optimizer.state, loss)
            value = float(loss.item())
            if not np.isfinite(value):
                raise ValueError('NONFINITE_TRAIN_LOSS')
            total += value*len(batch)
        item = dict(epoch=epoch, meanGroupLoss=total/len(groups), learningRate=.0001*.9**(epoch-1),
                    seconds=time.monotonic()-started, groupsSeen=len(groups))
        metrics['epochs'].append(item)
        write(OUT/'metrics.json', metrics)
        print('epoch', json.dumps(item), flush=True)
        if epoch in CHECKPOINTS:
            record('epoch-'+str(epoch), epoch)
    metrics['complete'] = True
    write(OUT/'metrics.json', metrics)
    print('training complete', flush=True)


def context_values(model, groups):
    result = []
    # Runtime-shaped float64 accumulation, bounded to one group of alternatives.
    for g in groups:
        encoded = [encode(g['prefix'], c) for c in g['candidates']]
        if not encoded:
            result.append([])
            continue
        x = np.concatenate([a for a, _ in encoded])
        y = np.concatenate([b for _, b in encoded])
        z = neural.logits(model, x)
        z -= z.max(axis=-1, keepdims=True)
        probabilities = np.exp(z)
        probabilities /= probabilities.sum(axis=-1, keepdims=True)
        logp = np.log(np.maximum(probabilities[np.arange(len(y)), y], 1e-9))
        offsets = np.cumsum([0]+[len(b) for _, b in encoded])
        result.append([float(np.clip((logp[a:b].mean()+3)*.25, -.5, .5)) for a, b in zip(offsets[:-1], offsets[1:])])
    return result


def summarize(groups, values):
    result = dict(typoRows=0, expectedAvailable=0, combinedTop1=0, neuralTop1=0, byEdit={}, controls=0)
    for g, neural_scores in zip(groups, values, strict=True):
        combined = np.asarray(g['tree'])+neural_scores
        def hit(scores):
            order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
            return int(bool(order) and g['labels'][order[0]])
        if not g['typo']:
            result['controls'] += 1
            continue
        result['typoRows'] += 1
        result['expectedAvailable'] += int(any(g['labels']))
        combined_hit, neural_hit = hit(combined), hit(neural_scores)
        result['combinedTop1'] += combined_hit
        result['neuralTop1'] += neural_hit
        bucket = result['byEdit'].setdefault(str(g['editCount']), dict(rows=0, expectedAvailable=0, combinedTop1=0, neuralTop1=0))
        bucket['rows'] += 1
        bucket['expectedAvailable'] += int(any(g['labels']))
        bucket['combinedTop1'] += combined_hit
        bucket['neuralTop1'] += neural_hit
    return result


def choose(models):
    if 'original' not in models:
        raise ValueError('ORIGINAL_REQUIRED')
    return min(models, key=lambda name: (-models[name]['newDev']['combinedTop1'],
                                         -models[name]['oldDev']['combinedTop1'],
                                         name != 'original', models[name]['epoch']))


def evaluate_dev():
    plan, data = read_frozen()
    if (OUT/'selection.json').exists():
        raise ValueError('SELECTION_ALREADY_FROZEN')
    metrics = json.loads((OUT/'metrics.json').read_text())
    require_hash(OUT/'plan.json', metrics['planSha256'])
    if not metrics['complete'] or set(metrics['models']) != {'original', 'epoch-1', 'epoch-2', 'epoch-4', 'epoch-6'}:
        raise ValueError('INCOMPLETE_CHECKPOINT_SET')
    report = dict(planSha256=sha(OUT/'plan.json'), models={}, coverage=plan['coverage'], testAccess=False)
    scores = {key: dict(rowIds=[g['id'] for g in data[key]], models={}) for key in ('newDev', 'oldDev')}
    for name, item in metrics['models'].items():
        require_hash(item['path'], item['sha256'])
        model = neural.load_model(item['path'])
        result = dict(item)
        for key in ('newDev', 'oldDev'):
            values = context_values(model, data[key])
            result[key] = summarize(data[key], values)
            scores[key]['models'][name] = values
        report['models'][name] = result
        print('dev', name, json.dumps(result), flush=True)
    selected = choose(report['models'])
    write(OUT/'dev-report.json', report)
    write(OUT/'dev-scores.json', scores)
    write(OUT/'selection.json', dict(selected=selected, selectedPath=report['models'][selected]['path'],
          selectedSha256=report['models'][selected]['sha256'], originalSha256=report['models']['original']['sha256'],
          rankerSha256=sha(ASSETS/'ru-ranker.bin'), planSha256=sha(OUT/'plan.json'), metricsSha256=sha(OUT/'metrics.json'),
          devReportSha256=sha(OUT/'dev-report.json'), devScoresSha256=sha(OUT/'dev-scores.json'),
          selectionFrozenBeforeTest=True, testAccess=False))
    print('selected', selected, report['models'][selected]['sha256'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'train', 'evaluate-dev'))
    args = parser.parse_args()
    {'prepare': prepare, 'train': train, 'evaluate-dev': evaluate_dev}[args.command]()
