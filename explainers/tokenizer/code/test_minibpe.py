"""Checks for minibpe.py. Run: python test_minibpe.py  (add --full to also retrain on TinyStories, ~4 min)."""
import json, os, pathlib, sys, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from minibpe import Tokenizer, count_pairs, merge_pair, SAMPLE
from collections import Counter

# 1. the two helpers do what their docstrings say
c = Counter(); count_pairs([104, 101, 108, 108, 111], c)
assert c == Counter({(104, 101): 1, (101, 108): 1, (108, 108): 1, (108, 111): 1})
assert merge_pair([104, 101, 108, 108, 111], (108, 108), 300) == [104, 101, 300, 111]
assert merge_pair([97, 97, 97], (97, 97), 256) == [256, 97]

# 2. decode(encode(x)) == x for awkward text
tok = Tokenizer(); tok.train(SAMPLE * 20, 300); tok.add_special_tokens(["<|endoftext|>"])
HARD = ["", " ", "\n\n", "Hello! The cat sat.", "HELLO hello Hello", "₹ 1,234.50", "🤦‍♂️ 🙂",
        "आप कैसे हैं?", "中文字符", "    def f(x):\n        return x", "a<|endoftext|>b", "<|endoftext|>"]
for s in HARD:
    assert tok.decode(tok.encode(s)) == s, s
assert tok.encode("<|endoftext|>") == [tok.special["<|endoftext|>"]]
assert len(tok.encode("<|endoftext|>", allow_special=False)) > 1

# 3. save then load gives a tokenizer that behaves identically
with tempfile.TemporaryDirectory() as d:
    path = os.path.join(d, "t.json"); tok.save(path); tok2 = Tokenizer.load(path)
assert tok2.merges == tok.merges and tok2.vocab == tok.vocab and tok2.special == tok.special
for s in HARD:
    assert tok2.encode(s) == tok.encode(s)
print("basic checks passed")

# 4. full check: same merges and same numbers as the explainer (demo/out/merges.txt, toy_bpe.json)
if "--full" in sys.argv:
    demo = pathlib.Path(__file__).resolve().parent.parent / "demo"
    text = (demo / "data" / "TinyStoriesV2-GPT4-valid.txt").read_text(encoding="utf-8").replace("<|endoftext|>", "\n")
    t0 = time.time(); big = Tokenizer(); big.train(text, 256 + 8000)
    print("trained 8,000 merges in %.0f s" % (time.time() - t0))
    ref = [line.split("\t") for line in (demo / "out" / "merges.txt").read_text(encoding="utf-8").splitlines()[1:]]
    # merges.txt shows half-characters as "�" (decode with errors="replace"), so compare the same way
    ours = [repr(big.vocab[i].decode("utf-8", "replace")) for i in big.merges.values()]
    assert ours == [r[3] for r in ref], "merge list differs from the explainer's"
    toy = json.loads((demo / "out" / "toy_bpe.json").read_text(encoding="utf-8"))
    for word, info in toy["watch"].items():
        assert [[i, big.piece(i)] for i in big.encode(word)] == [list(x) for x in info["encoded"]], word
    unseen = (demo / "data" / "TinyStoriesV2-GPT4-train-first5MB.txt").read_bytes().decode("utf-8", "ignore").replace("<|endoftext|>", "\n")
    n = len(big.encode(unseen, allow_special=False))
    fp = json.loads((demo / "out" / "fp.json").read_text(encoding="utf-8"))
    assert n == fp["curve"]["points"][-1]["tokens"], (n, fp["curve"]["points"][-1]["tokens"])
    assert big.decode(big.encode(unseen[:200000])) == unseen[:200000]
    print("full check passed: identical merges, hello splits and %d tokens on unseen text" % n)
