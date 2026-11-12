"""Calculate Character Error Rate for a reference and a model transcription."""

import argparse
from pathlib import Path


def edit_distance(reference: str, hypothesis: str) -> int:
    """Return the number of single-character edits between two strings."""
    # Dynamic programming: each cell stores the edit distance for two prefixes.
    previous_row = list(range(len(hypothesis) + 1))

    for ref_index, ref_char in enumerate(reference, start=1):
        current_row = [ref_index]
        for hyp_index, hyp_char in enumerate(hypothesis, start=1):
            substitution_cost = 0 if ref_char == hyp_char else 1
            current_row.append(
                min(
                    current_row[-1] + 1,  # insert a character
                    previous_row[hyp_index] + 1,  # delete a character
                    previous_row[hyp_index - 1] + substitution_cost,
                )
            )
        previous_row = current_row

    return previous_row[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Calculate CER after making runs of whitespace consistent."""
    reference = " ".join(reference.split())
    hypothesis = " ".join(hypothesis.split())

    if not reference:
        return 0.0 if not hypothesis else 1.0

    return edit_distance(reference, hypothesis) / len(reference)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare a transcription with its reference.")
    parser.add_argument("reference", type=Path, help="Path to the manually corrected text")
    parser.add_argument("hypothesis", type=Path, help="Path to the model transcription")
    args = parser.parse_args()

    reference = args.reference.read_text(encoding="utf-8")
    hypothesis = args.hypothesis.read_text(encoding="utf-8")
    score = character_error_rate(reference, hypothesis)
    print(f"CER: {score:.2%}")


if __name__ == "__main__":
    main()
