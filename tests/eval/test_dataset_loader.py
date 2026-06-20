from __future__ import annotations

import json

import pytest

from openminion_eval import (
    DATASET_VERSION,
    EvalDatasetValidationError,
    hash_eval_dataset,
    load_eval_dataset,
    load_eval_dataset_json,
    load_eval_dataset_jsonl,
)


def _case(case_id: str, expected: str = "hi") -> dict:
    return {
        "id": case_id,
        "name": f"case-{case_id}",
        "turns": [{"user": "hello", "expected": expected}],
        "tags": ["smoke"],
    }


def test_load_eval_dataset_json_accepts_versioned_cases(tmp_path) -> None:
    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "name": "starter",
                "metadata": {"owner": "eval"},
                "cases": [_case("a"), _case("b")],
            }
        ),
        encoding="utf-8",
    )

    dataset = load_eval_dataset_json(path)

    assert dataset.dataset_version == DATASET_VERSION
    assert dataset.name == "starter"
    assert dataset.metadata == {"owner": "eval"}
    assert [case.case_id for case in dataset.cases] == ["a", "b"]
    assert [transcript.name for transcript in dataset.transcripts] == [
        "case-a",
        "case-b",
    ]


def test_load_eval_dataset_dispatches_by_jsonl_suffix(tmp_path) -> None:
    path = tmp_path / "dataset.jsonl"
    path.write_text(
        "\n".join(json.dumps(_case(case_id)) for case_id in ("first", "second")),
        encoding="utf-8",
    )

    dataset = load_eval_dataset(path)

    assert dataset.name == "dataset"
    assert [case.case_id for case in dataset.cases] == ["first", "second"]


def test_load_eval_dataset_jsonl_preserves_file_order(tmp_path) -> None:
    path = tmp_path / "ordered.jsonl"
    path.write_text(
        "\n".join(json.dumps(_case(case_id)) for case_id in ("b", "a", "c")),
        encoding="utf-8",
    )

    dataset = load_eval_dataset_jsonl(path, name="ordered")

    assert dataset.name == "ordered"
    assert [case.case_id for case in dataset.cases] == ["b", "a", "c"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"dataset_version": "2", "name": "bad", "cases": []}, "unsupported"),
        ({"dataset_version": DATASET_VERSION, "name": "bad"}, "cases"),
        (
            {
                "dataset_version": DATASET_VERSION,
                "name": "bad",
                "cases": [{"id": "dup", "turns": []}, {"id": "dup", "turns": []}],
            },
            "duplicate case id",
        ),
        (
            {"dataset_version": DATASET_VERSION, "name": "bad", "cases": [{"id": "x"}]},
            "turns",
        ),
    ],
)
def test_load_eval_dataset_json_rejects_invalid_inputs(
    tmp_path, payload: dict, message: str
) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EvalDatasetValidationError, match=message):
        load_eval_dataset_json(path)


def test_load_eval_dataset_jsonl_rejects_bad_record(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("{}\nnot-json", encoding="utf-8")

    with pytest.raises(EvalDatasetValidationError, match="invalid JSONL record"):
        load_eval_dataset_jsonl(path)


def test_hash_eval_dataset_is_stable_and_content_sensitive(tmp_path) -> None:
    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "name": "stable",
                "cases": [_case("a"), _case("b")],
            }
        ),
        encoding="utf-8",
    )
    changed_path = tmp_path / "changed.json"
    changed_path.write_text(
        json.dumps(
            {
                "dataset_version": DATASET_VERSION,
                "name": "stable",
                "cases": [_case("a"), _case("b", expected="bye")],
            }
        ),
        encoding="utf-8",
    )

    dataset = load_eval_dataset_json(path)

    assert hash_eval_dataset(dataset) == hash_eval_dataset(load_eval_dataset_json(path))
    assert hash_eval_dataset(dataset) != hash_eval_dataset(
        load_eval_dataset_json(changed_path)
    )


def test_hash_eval_dataset_ignores_jsonl_source_filename(tmp_path) -> None:
    content = "\n".join(json.dumps(_case(case_id)) for case_id in ("a", "b"))
    first_path = tmp_path / "first.jsonl"
    second_path = tmp_path / "second.jsonl"
    first_path.write_text(content, encoding="utf-8")
    second_path.write_text(content, encoding="utf-8")

    assert hash_eval_dataset(load_eval_dataset_jsonl(first_path)) == hash_eval_dataset(
        load_eval_dataset_jsonl(second_path)
    )
