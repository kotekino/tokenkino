# --------------------------------------------------------------
# TEXT UTILITIES
# --------------------------------------------------------------

# remove extra spaces
def util_removeSpace(tokens: str) -> str:
    # trim
    result = tokens.strip()

    # remove inside spaces
    result = " ".join(result.split())

    # return result
    return result

