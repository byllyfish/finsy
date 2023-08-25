"Implements string utility functions."

# Copyright (c) 2022-2023 Bill Fisher
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
    row = list(range(len2 + 1))

    for i in range(len1):
        prev = i + 1
        for j in range(len2):
            min_cost = row[j]
            if str1[i] != str2[j]:
                min_cost += 1

                delete = row[j + 1] + 1
                if delete < min_cost:
                    min_cost = delete

                insert = prev + 1
                if insert < min_cost:
                    min_cost = insert

            row[j] = prev
            prev = min_cost

        row[len2] = prev

    return row[len2]
