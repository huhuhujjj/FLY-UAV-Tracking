"""Behavior checks for the local three-class ignore policy."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from visdrone_det_ignore import covered_fraction, prepare_image


def row(box, category, score=1):
    return {'bbox_xywh': box, 'source_category': category, 'score': score}


def det(box, category=0, score=0.8):
    return {'bbox_xywh': box, 'local_class': category, 'score': score}


class IgnorePolicyTests(unittest.TestCase):
    def test_two_regions_union_above_half(self):
        self.assertAlmostEqual(covered_fraction((0, 0, 10, 10),
                               [(0, 0, 3, 10), (7, 0, 3, 10)], 20, 20), 0.6)

    def test_overlap_is_not_counted_twice(self):
        self.assertAlmostEqual(covered_fraction((0, 0, 10, 10),
                               [(0, 0, 4, 10), (2, 0, 4, 10)], 20, 20), 0.6)

    def test_exact_half_is_ignored_for_gt_and_prediction(self):
        result = prepare_image([row((0, 0, 5, 10), 0), row((0, 0, 10, 10), 4)],
                               [det((0, 0, 10, 10))], 20, 20)
        self.assertEqual(result['counts']['target_boxes_ignored'], 1)
        self.assertEqual(result['counts']['detections_ignored'], 1)

    def test_others_is_ignored_but_van_is_not(self):
        result = prepare_image([row((0, 0, 10, 10), 11, 0),
                                row((10, 0, 10, 10), 5)],
                               [det((0, 0, 10, 10)), det((10, 0, 10, 10))], 20, 20)
        self.assertEqual(result['counts']['detections_ignored'], 1)
        self.assertEqual(result['detections'][0]['bbox_xywh'], (10, 0, 10, 10))

    def test_source_boxes_outside_image_fail(self):
        with self.assertRaises(ValueError):
            prepare_image([row((19, 0, 2, 2), 0, 0)], [], 20, 20)


if __name__ == '__main__':
    unittest.main()
