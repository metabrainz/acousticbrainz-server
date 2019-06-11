def remove_duplicates(arr):
    seen = set()
    return [x for x in arr if not (x in seen or seen.add(x))]