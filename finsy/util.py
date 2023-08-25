"Implements various utility functions."


def minimum_edit_distance(str1: str, str2: str) -> int:
    """Compute the minimum edit distance between two strings.

    Computes the Levenshtein distance using the iterative Wagner-Fischer
    algorithm.

    Reference:  https://en.wikipedia.org/wiki/Levenshtein_distance
      See "Iterative with two matrix rows"
      Replace `v1` accesses with `prev` to eliminate second row `v1`.
    """
    if str1 == str2:
        return 0

    len1 = len(str1)
    len2 = len(str2)
    v0 = list(range(len2 + 1))

    for i in range(0, len1):
        prev = i + 1
        for j in range(0, len2):
            min_cost = v0[j]
            if str1[i] != str2[j]:
                min_cost += 1

                delete = v0[j + 1] + 1
                if delete < min_cost:
                    min_cost = delete

                insert = prev + 1
                if insert < min_cost:
                    min_cost = insert

            v0[j] = prev
            prev = min_cost

        v0[len2] = prev

    return v0[len2]
