"""Hand-calculated conversion and schema regressions, independent of pilot data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_visdrone import parse_line,eligible,yolo,decode_yolo


class ConversionTests(unittest.TestCase):
    def test_hand_calculated_box_and_class(self):
        r=parse_line('10,20,40,60,1,4,0,2','DET',1)
        self.assertEqual(yolo(r,100,200),'0 0.30000000 0.25000000 0.40000000 0.30000000')
        c,box=decode_yolo(yolo(r,100,200),100,200)
        self.assertEqual(c,0)
        for got,expected in zip(box,[10,20,40,60]):self.assertAlmostEqual(got,expected)

    def test_bus_truck_mapping(self):
        for source,local in [(9,1),(6,2)]:
            self.assertEqual(parse_line(f'0,0,1,1,1,{source},0,0','DET',1)['local_class'],local)

    def test_ignore_van_others_never_become_targets(self):
        for score,category in [(0,4),(1,5),(1,0),(1,11)]:
            r=parse_line(f'0,0,1,1,{score},{category},0,0','DET',1)
            self.assertFalse(eligible(r,100,100));self.assertEqual(r['raw_fields'][5],category)

    def test_mot_ids_attributes_and_frame_are_lossless(self):
        r=parse_line('19,42,10,20,30,40,1,6,1,2,','MOT',7)
        self.assertEqual([r['frame_index'],r['target_id'],r['truncation'],r['occlusion']],[19,42,1,2])
        self.assertEqual(r['source_line'],7)

    def test_bounds_are_not_silently_clipped(self):
        r=parse_line('-1,2,4,5,1,4,0,0','DET',1)
        self.assertFalse(eligible(r,100,100));self.assertEqual(r['bbox_xywh'],[-1,2,4,5])
        self.assertTrue(eligible(parse_line('0,0,100,100,1,4,0,0','DET',1),100,100))

    def test_source_id_zero_is_valid(self):
        self.assertEqual(parse_line('1,0,0,0,10,10,1,4,0,0','MOT',1)['target_id'],0)

    def test_malformed_annotations_fail(self):
        for line in ['0,0,0,1,1,4,0,0','0,0,1,1,1,12,0,0','0,0,1,1,1,4,0','0,0,nan,1,1,4,0,0']:
            with self.assertRaises(ValueError):parse_line(line,'DET',1)


if __name__=='__main__':unittest.main()
