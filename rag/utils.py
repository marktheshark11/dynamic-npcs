def remove_duplicates(claims):
    seen = set()
    unique = []
    for claim in claims:
        if claim["id"] not in seen:
            seen.add(claim["id"])
            unique.append(claim)
    return unique
