Aggregate `ext1` results:

```text
current: p=0.731 r=0.776 f1=0.753
stanza:  p=0.736 r=0.702 f1=0.718
hybrid:  p=0.817 r=0.827 f1=0.822
```

Hybrid policy now:
```text
de -> Stanza
fr -> Stanza
hy -> Stanza
jp -> current
kr -> current
ar -> current for now
```

Per-language hybrid aggregate:
```text
ar f1=0.551
de f1=0.860
fr f1=0.931
hy f1=0.904
jp f1=0.849
kr f1=0.924
```

Aggregate `ext2` results after Arabic unvocalized-prefix fix:

```text
current: p=0.790 r=0.830 f1=0.809
hybrid:  p=0.866 r=0.868 f1=0.867
```

Hybrid policy for `ext2`:
```text
de -> Stanza
fr -> Stanza
hy -> Stanza
jp -> current
kr -> current
ar -> current
```

Per-language `ext2` hybrid aggregate:
```text
ar f1=0.693
de f1=0.911
fr f1=0.949
hy f1=0.859
jp f1=0.842
kr f1=0.921
```

Aggregate `ext3_new_langs` results after adding `es`, `fi`, and `it` support:

```text
current: p=0.861 r=0.876 f1=0.868
hybrid:  p=0.861 r=0.876 f1=0.868
```

Hybrid policy for `ext3_new_langs`:
```text
es -> current/simplemma
fi -> current/simplemma
it -> current/simplemma
```

Per-language `ext3_new_langs` aggregate:
```text
es f1=0.823
fi f1=0.897
it f1=0.884
```

Aggregate `ext4_new_langs` results after adding `pt`, `tr`, and `vi` support:

```text
raw:       p=0.427 r=0.636 f1=0.511
reference: p=0.950 r=0.969 f1=0.960
```

`ext4_new_langs` uses `--reference-vocabulary` because Vietnamese target lemmas are mostly multiword phrases.

Hybrid policy for `ext4_new_langs`:
```text
pt -> current/simplemma + Portuguese candidates
tr -> current/simplemma + Turkish suffix candidates
vi -> reference phrase matcher
```

Per-language `ext4_new_langs` reference aggregate:
```text
pt f1=0.972
tr f1=0.928
vi f1=1.000
```
