import copy
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from foodarena.api import create_server
from foodarena.ranker import ROOT, read_json, recommend
from foodarena.train import synthetic_pairs, train


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.request = read_json(ROOT / "examples" / "request.json")

    def test_constraints_and_unknown_allergens(self):
        result = recommend(self.request)
        names = {d["id"] for d in result["recommendations"]}
        self.assertNotIn("sesame-noodles", names)
        excluded = {d["id"]: d["reasons"] for d in result["excluded"]}
        self.assertIn("过敏原信息未核实", excluded["seasonal"])
        self.assertIn("超出预算", excluded["fish-rice"])
        self.assertIn("已售罄", excluded["sold-out"])
        self.assertIn("超过辣度上限", excluded["spicy-chicken"])

    def test_vegetarian_and_dislike(self):
        self.request["profile"].update(vegetarian=True, disliked_ingredients=["鸡蛋"])
        self.request["top_k"] = 20
        result = recommend(self.request)
        self.assertEqual([d["id"] for d in result["recommendations"]], ["tofu-rice"])

    def test_no_match_never_relaxes_constraints(self):
        self.request["profile"]["budget"] = 1
        result = recommend(self.request)
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["recommendations"], [])

    def test_invalid_preferences(self):
        for field, value in [("budget", float("nan")), ("budget", True), ("budget", -1),
                             ("max_spice", 9), ("allergens", "花生"), ("vegetarian", "false")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                request = copy.deepcopy(self.request)
                request["profile"][field] = value
                recommend(request)

    def test_unknown_fields_fail_closed(self):
        self.request["profile"]["allergies"] = ["花生"]
        with self.assertRaises(ValueError):
            recommend(self.request)

    def test_missing_allergen_metadata_rejected(self):
        self.request["dishes"] = read_json(ROOT / "data" / "menu.sample.json")[:1]
        del self.request["dishes"][0]["allergens_verified"]
        with self.assertRaises(ValueError):
            recommend(self.request)

    def test_empty_menu_and_top_k(self):
        self.request["dishes"] = []
        self.assertEqual(recommend(self.request)["status"], "no_match")
        self.request["top_k"] = True
        with self.assertRaises(ValueError):
            recommend(self.request)

    def test_order_and_explanation(self):
        items = recommend(self.request)["recommendations"]
        self.assertEqual([i["score"] for i in items], sorted([i["score"] for i in items], reverse=True))
        for item in items:
            self.assertAlmostEqual(item["score"], sum(x["contribution"] for x in item["explanation"]), places=3)

    def test_training_reproducible(self):
        rows = synthetic_pairs(count=120)
        first = train(rows, epochs=30)
        second = train(rows, epochs=30)
        self.assertEqual(first, second)
        self.assertTrue(any(abs(w) > 0.01 for w in first[0]["weights"]))
        self.assertEqual(first[1]["validation_pairs"], 24)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_health(self):
        with urlopen(self.base + "/health", timeout=3) as response:
            self.assertEqual(json.load(response)["status"], "ok")

    def test_recommend(self):
        payload = read_json(ROOT / "examples" / "request.json")
        request = Request(self.base + "/recommend", json.dumps(payload).encode(), {"Content-Type": "application/json"})
        with urlopen(request, timeout=3) as response:
            self.assertEqual(len(json.load(response)["recommendations"]), 3)

    def test_invalid_json(self):
        request = Request(self.base + "/recommend", b"{", {"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=3)
        self.assertEqual(error.exception.code, 400)

    def test_wrong_content_type(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.base + "/recommend", b"{}"), timeout=3)
        self.assertEqual(error.exception.code, 415)


if __name__ == "__main__":
    unittest.main()
