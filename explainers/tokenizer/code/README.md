# minibpe: build your own tokenizer

A complete byte-level BPE tokenizer in one Python file, using the same recipe as GPT-2:
cut text into word-sized chunks (a space stays on the front of a word), start from the
256 byte values, and repeatedly glue the most frequent neighbouring pair into a new piece.

It trains on any text file, encodes, decodes, handles special tokens such as
`<|endoftext|>`, and saves and loads itself as JSON.

## Run it

```
pip install regex
python minibpe.py                    # train on a small built-in sample (list size 300)
python minibpe.py my_text.txt 1000   # train on your own text file (list size 1000)
```

## Use it from your own code

```python
from minibpe import Tokenizer

tok = Tokenizer()
tok.train(open("my_text.txt", encoding="utf-8").read(), 2000)
ids = tok.encode("Hello world")
print(ids, [tok.piece(i) for i in ids])
print(tok.decode(ids))           # gives back "Hello world"
tok.save("my_tokenizer.json")
tok2 = Tokenizer.load("my_tokenizer.json")
```

## Tests

```
python test_minibpe.py           # helpers, exact round trips, save/load
python test_minibpe.py --full    # also retrains on TinyStories (22 MB, a few minutes)
```

The full test checks that this file reproduces the measurements in the tokenizer explainer
exactly: the same 8,000 merges, the same splits of hello / Hello / HELLO, and the same
token count on unseen stories.

## Files

- `minibpe.py`: the tokenizer (about 200 lines, heavily commented)
- `test_minibpe.py`: the tests
