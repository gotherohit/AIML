r"""
minibpe.py - a complete byte-level BPE tokenizer in one file.

It uses the same recipe as GPT-2's tokenizer:
  step 0: cut the text into word-sized chunks with a fixed pattern (a space stays on the front of a word)
  step 1: write every chunk as its UTF-8 bytes (256 possible values = the starting list)
  step 2: count every pair of neighbouring pieces, glue the most frequent pair into a new piece
  step 3: repeat until the list has the size you asked for

What you need:
  Python 3.8 or newer
  the "regex" package (pip install regex). Python's built-in "re" module does not understand
  \p{L} ("any letter in any language"), which the GPT-2 pattern needs.

Try it:
  python minibpe.py                      train on a small built-in sample
  python minibpe.py my_text.txt 1000     train on your own text file, list size 1000
"""

import json
import sys
from collections import Counter

import regex

# Step 0 pattern, copied from GPT-2 (OpenAI's tiktoken library, "gpt2" encoding).
# Read it as "try these alternatives, left to right":
#   '(?:[sdmt]|ll|ve|re)   English endings after an apostrophe: 's 't 're 've 'm 'll 'd
#    ?\p{L}+               an optional space, then one or more letters        ( hello)
#    ?\p{N}+               an optional space, then one or more digits         ( 2024)
#    ?[^\s\p{L}\p{N}]+     an optional space, then other symbols              ( !!)
#   \s+(?!\S)              a run of spaces, leaving the last one for the next word
#   \s+                    any other run of spaces / new lines
GPT2_SPLIT_PATTERN = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""


def count_pairs(ids, counts, weight=1):
    """Add every neighbouring pair in the list `ids` to the Counter `counts`.

    Example: ids = [104, 101, 108, 108, 111]  ("hello")
    pairs:   (104,101) (101,108) (108,108) (108,111), each counted `weight` times.
    """
    for pair in zip(ids, ids[1:]):
        counts[pair] += weight


def merge_pair(ids, pair, new_id):
    """Return a new list where every occurrence of `pair` side by side is replaced by `new_id`.

    Example: merge_pair([104, 101, 108, 108, 111], (108, 108), 300)  ->  [104, 101, 300, 111]
    """
    out = []
    i = 0
    while i < len(ids):
        if i + 1 < len(ids) and ids[i] == pair[0] and ids[i + 1] == pair[1]:
            out.append(new_id)   # found the pair: write the new piece, skip both
            i += 2
        else:
            out.append(ids[i])   # not the pair: copy this piece unchanged
            i += 1
    return out


class Tokenizer:
    """Holds what a tokenizer knows, and the four things it can do: train, encode, decode, save/load."""

    def __init__(self, pattern=GPT2_SPLIT_PATTERN):
        self.pattern = pattern
        self.splitter = regex.compile(pattern)
        # merges: (left id, right id) -> new id. Python dicts remember insertion order,
        # so this is also the order in which the merges were learned.
        self.merges = {}
        # vocab: id -> the bytes that piece stands for. It starts with the 256 single bytes.
        self.vocab = {i: bytes([i]) for i in range(256)}
        # special tokens: name -> id, e.g. "<|endoftext|>" -> 1000. Added by hand, never learned.
        self.special = {}

    # ------------------------------------------------------------------ training
    def train(self, text, vocab_size, verbose=False):
        """Learn (vocab_size - 256) merges from `text`."""
        if vocab_size < 256:
            raise ValueError("vocab_size must be at least 256 (the single bytes)")
        if self.merges:
            raise ValueError("this tokenizer is already trained; make a new Tokenizer()")

        # Step 0: cut into chunks, and count how often each different chunk appears.
        # Most chunks repeat (" the" appears thousands of times), so we keep each different
        # chunk once together with its count. Much less work than looking at every copy.
        chunk_counts = Counter(self.splitter.findall(text))

        # Step 1: every chunk becomes its list of byte values.
        words = [[list(chunk.encode("utf-8")), count] for chunk, count in chunk_counts.items()]

        for step in range(vocab_size - 256):
            # Step 2a: count every neighbouring pair inside every chunk.
            pair_counts = Counter()
            for ids, count in words:
                count_pairs(ids, pair_counts, count)
            if not pair_counts:
                break  # every chunk is already a single piece: nothing left to merge

            # Step 2b: the most frequent pair wins. If two pairs tie, the one with the smaller
            # ids wins, so training always gives the same result for the same text.
            best = max(pair_counts, key=lambda p: (pair_counts[p], -p[0], -p[1]))
            new_id = 256 + step

            # Step 2c: glue the winner everywhere, and remember the rule.
            for word in words:
                word[0] = merge_pair(word[0], best, new_id)
            self.merges[best] = new_id
            self.vocab[new_id] = self.vocab[best[0]] + self.vocab[best[1]]

            if verbose:
                print("merge %d: %r + %r -> %r  (seen %d times)" % (
                    step + 1, self.piece(best[0]), self.piece(best[1]), self.piece(new_id), pair_counts[best]))

    def add_special_tokens(self, names):
        """Give hand-made marker tokens the next free ids. Call this after train()."""
        for name in names:
            if name not in self.special:
                self.special[name] = len(self.vocab) + len(self.special)

    # ------------------------------------------------------------------ encoding
    def _encode_chunk(self, chunk_bytes):
        """Turn one chunk's bytes into ids by replaying the learned merges, earliest first."""
        ids = list(chunk_bytes)
        while len(ids) >= 2:
            # Of all neighbouring pairs, find the one whose merge was learned earliest
            # (smallest new id). Pairs with no merge get "infinity", so they never win.
            pair = min(zip(ids, ids[1:]), key=lambda p: self.merges.get(p, float("inf")))
            if pair not in self.merges:
                break  # no neighbouring pair has a rule: we are done
            ids = merge_pair(ids, pair, self.merges[pair])
        return ids

    def encode(self, text, allow_special=True):
        """Text -> list of ids."""
        ids = []
        if allow_special and self.special:
            # Cut the text around the special tokens first, so "<|endoftext|>" becomes one id
            # instead of being spelled out as < | e n d ...
            names = sorted(self.special, key=len, reverse=True)
            parts = regex.split("(" + "|".join(regex.escape(n) for n in names) + ")", text)
        else:
            parts = [text]
        for part in parts:
            if part in self.special and allow_special:
                ids.append(self.special[part])
                continue
            for chunk in self.splitter.findall(part):
                ids.extend(self._encode_chunk(chunk.encode("utf-8")))
        return ids

    # ------------------------------------------------------------------ decoding
    def decode(self, ids):
        """List of ids -> text. Join every piece's bytes, then read them as UTF-8."""
        special_by_id = {i: name for name, i in self.special.items()}
        data = b"".join(special_by_id[i].encode("utf-8") if i in special_by_id else self.vocab[i] for i in ids)
        # errors="replace": if the ids end in the middle of a character (half an emoji),
        # show the replacement mark instead of crashing.
        return data.decode("utf-8", errors="replace")

    def piece(self, token_id):
        """The text one id stands for, for printing. A half character shows as its byte values."""
        for name, i in self.special.items():
            if i == token_id:
                return name
        b = self.vocab[token_id]
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            return "<bytes " + " ".join(str(x) for x in b) + ">"

    # ------------------------------------------------------------------ save / load
    def save(self, path):
        """Write everything needed to rebuild this tokenizer to a JSON file."""
        data = {
            "pattern": self.pattern,
            "merges": [[a, b] for (a, b) in self.merges],   # in learned order
            "special": self.special,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)

    @classmethod
    def load(cls, path):
        """Read a file written by save() and rebuild the tokenizer."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        tok = cls(data["pattern"])
        for step, (a, b) in enumerate(data["merges"]):
            new_id = 256 + step
            tok.merges[(a, b)] = new_id
            tok.vocab[new_id] = tok.vocab[a] + tok.vocab[b]
        tok.special = data["special"]
        return tok


# ---------------------------------------------------------------------- demo
SAMPLE = """Once upon a time there was a little cat. The cat liked to sit in the sun.
One day the cat saw a big dog. "Hello!" said the cat. "Hello," said the dog.
The cat and the dog played in the sun all day, and then they went home to sleep.
"""

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
        size = int(sys.argv[2]) if len(sys.argv) >= 3 else 1000
    else:
        text, size = SAMPLE * 20, 300

    tok = Tokenizer()
    tok.train(text, size, verbose=True)
    tok.add_special_tokens(["<|endoftext|>"])
    tok.save("my_tokenizer.json")
    print("\nlearned %d merges, list size %d (+%d special), saved to my_tokenizer.json"
          % (len(tok.merges), len(tok.vocab), len(tok.special)))

    for test in ["Hello! The cat sat in the sun.", "hello HELLO", "₹ 🙂<|endoftext|>"]:
        ids = tok.encode(test)
        print("\n%r" % test)
        print("  ids:    %s" % ids)
        print("  pieces: %s" % " | ".join(tok.piece(i) for i in ids))
        assert tok.decode(ids) == test, "decode(encode(text)) must give back the same text"
    print("\ndecode(encode(text)) gave back the exact text every time.")
