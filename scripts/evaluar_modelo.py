import numpy as np
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             balanced_accuracy_score, roc_auc_score)

d = np.load("logits_test.npz")
lg, y = d["logits"].astype(np.float64), d["labels"].astype(int)
keep = np.load("clean_test_mask.npy")      # bool (12705,) o índices; ajusta al nombre real
if keep.dtype != bool:
    m = np.zeros(len(y), bool); m[keep] = True; keep = m
assert keep.sum() == 4079

z = lg - lg.max(1, keepdims=True)
p = np.exp(z); p /= p.sum(1, keepdims=True)       # softmax SIN temperatura
pred, conf = p.argmax(1), p.max(1)

# --- subconjunto ---
ys, ps, pr = y[keep], p[keep], pred[keep]
P, R, F, _ = precision_recall_fscore_support(ys, pr, average="macro", zero_division=0)
print("acc", accuracy_score(ys, pr), "macroP", P, "macroR", R, "macroF1", F,
      "bal_acc", balanced_accuracy_score(ys, pr))
cls = [c for c in range(p.shape[1]) if 0 < (ys == c).sum() < len(ys)]
auc = np.mean([roc_auc_score(ys == c, ps[:, c]) for c in cls])
print("AUC OvR macro (clases presentes):", auc, "| clases usadas:", len(cls), "de", p.shape[1])

# --- cobertura REAL de la API (sin temperatura), conjunto de prueba completo ---
ok = pred == y
for t in (0.5, 0.6, 0.7, 0.8):
    k = conf >= t
    print(f"umbral {t}: cobertura {k.mean():.4f}  precision {ok[k].mean():.4f}  rechazadas {int((~k).sum())}")