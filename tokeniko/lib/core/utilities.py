# --------------------------------------------------------------
# TEXT UTILITIES
# --------------------------------------------------------------
import re

# remove extra spaces
def util_removeSpace(tokens: str) -> str:
    # trim
    result = tokens.strip()

    # remove inside spaces
    result = " ".join(result.split())

    # return result
    return result

# english contractions -> expanded form.
# stanza's neural tokenizer mis-merges some short-input contractions (e.g. "I'm",
# "he's") instead of splitting them into subject + copula/aux, so we normalize them
# upstream. only contractions whose expansion is unambiguous (or a pronoun/wh-word +
# copula/aux) are listed; noun possessives like "the cat's toy" are deliberately NOT
# here so they stay untouched.
_CONTRACTIONS = {
    "i'm": "i am",
    "you're": "you are", "we're": "we are", "they're": "they are",
    "he's": "he is", "she's": "she is", "it's": "it is", "that's": "that is",
    "there's": "there is", "here's": "here is", "what's": "what is",
    "who's": "who is", "where's": "where is", "how's": "how is", "let's": "let us",
    "i've": "i have", "you've": "you have", "we've": "we have", "they've": "they have",
    "i'll": "i will", "you'll": "you will", "he'll": "he will", "she'll": "she will",
    "we'll": "we will", "they'll": "they will", "it'll": "it will",
    "i'd": "i would", "you'd": "you would", "he'd": "he would", "she'd": "she would",
    "we'd": "we would", "they'd": "they would",
    "can't": "can not", "cannot": "can not", "won't": "will not", "shan't": "shall not",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "wouldn't": "would not", "couldn't": "could not", "shouldn't": "should not",
    "mustn't": "must not", "mightn't": "might not", "needn't": "need not",
}
_CONTRACTIONS_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _CONTRACTIONS) + r")\b", re.IGNORECASE
)

# expand english contractions ("I'm" -> "I am") before tokenization
def util_expandContractions(tokens: str) -> str:
    # normalize curly apostrophe to straight
    text = tokens.replace("’", "'")

    def _replace(match: "re.Match") -> str:
        word = match.group(1)
        expanded = _CONTRACTIONS[word.lower()]
        # preserve leading capitalization (e.g. "I'm" -> "I am", not "i am")
        if word[0].isupper():
            expanded = expanded[0].upper() + expanded[1:]
        return expanded

    return _CONTRACTIONS_RE.sub(_replace, text)

# --------------------------------------------------------------
# VECTOR UTILITIES
# --------------------------------------------------------------

