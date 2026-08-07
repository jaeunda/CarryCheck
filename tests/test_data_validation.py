import copy
import tempfile
import unittest
from pathlib import Path

from airline_baggage_agent.domain.baggage import load_rule_dataset
from airline_baggage_agent.domain.data_validation import (
    load_json_dataset,
    validate_baggage_dataset,
    validate_country_dataset,
)
from airline_baggage_agent.policies.country_agent import load_country_rule_dataset
from airline_baggage_agent.policies.japan_policy import load_japan_rule_dataset


class RuleDatasetValidationTests(unittest.TestCase):
    def test_duplicate_json_keys_fail_fast(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"dataset": {}, "dataset": {}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key: dataset"):
                load_json_dataset(path)

    def test_all_committed_datasets_are_valid(self):
        validate_baggage_dataset(load_rule_dataset())
        validate_country_dataset(load_country_rule_dataset())
        validate_country_dataset(load_japan_rule_dataset())

    def test_duplicate_rule_ids_fail_fast(self):
        dataset = copy.deepcopy(load_rule_dataset())
        dataset["rules"].append(copy.deepcopy(dataset["rules"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate rule_id"):
            validate_baggage_dataset(dataset)

    def test_non_https_sources_fail_fast(self):
        dataset = copy.deepcopy(load_country_rule_dataset())
        dataset["rules"][0]["source_url"] = "http://example.com/rule"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            validate_country_dataset(dataset)


if __name__ == "__main__":
    unittest.main()
