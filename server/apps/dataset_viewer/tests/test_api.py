from django.test import TestCase
from rest_framework.test import APIClient
from dataset_viewer.models import Dataset, DatasetItem
import json
import tempfile
from pathlib import Path
import shutil

class DatasetAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_datasets_list_empty(self):
        resp = self.client.get("/api/datasets/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_scan_invalid_dir(self):
        resp = self.client.post(
            "/api/datasets/scan",
            {"name": "ds", "root_dir": "/no/such/dir"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_dataset_items_empty(self):
        ds = Dataset.objects.create(name="ds1", root_dir="/tmp")
        resp = self.client.get(f"/api/datasets/{ds.id}/items")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {"count": 0, "page": 1, "page_size": 50, "results": []},
        )

    def test_item_detail_and_delete(self):
        ds = Dataset.objects.create(name="ds1", root_dir="/tmp")
        item = DatasetItem.objects.create(
            dataset=ds,
            image_path="images/1.jpg",
            width=10,
            height=20,
            sha256="abcd",
        )

        # List should include URLs
        resp_list = self.client.get(f"/api/datasets/{ds.id}/items")
        self.assertEqual(resp_list.status_code, 200)
        lst = resp_list.json()["results"][0]
        self.assertIn("image_url", lst)
        self.assertIn("thumb_url", lst)

        # Detail
        resp = self.client.get(f"/api/datasets/{ds.id}/items/{item.id}/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], item.id)
        self.assertEqual(data["image_path"], "images/1.jpg")
        self.assertIn("image_url", data)
        self.assertIn("thumb_url", data)

        # Wrong dataset -> 404
        resp404 = self.client.get(f"/api/datasets/{ds.id + 1}/items/{item.id}/")
        self.assertEqual(resp404.status_code, 404)

        # Delete
        resp_del = self.client.delete(f"/api/datasets/{ds.id}/items/{item.id}/")
        self.assertIn(resp_del.status_code, (200, 204))
        self.assertEqual(DatasetItem.objects.count(), 0)

0)

    def _create_dataset_with_items(self):
        root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        ds = Dataset.objects.create(
            name=f"ds{Dataset.objects.count() + 1}", root_dir=root
        )
        Path(root, "images").mkdir(parents=True, exist_ok=True)
        for i in (1, 2):
            DatasetItem.objects.create(
                dataset=ds,
                image_path=f"images/{i}.jpg",
                width=1,
                height=1,
                sha256=f"h{i}",
            )
        return ds, root

    def test_export_and_import_metadata(self):
        ds, root = self._create_dataset_with_items()

        # Prepare caption files
        item1 = DatasetItem.objects.get(dataset=ds, image_path="images/1.jpg")
        cap1 = Path(root, "images/1.json")
        cap1.write_text(
            json.dumps({"title": "t1", "caption": "c1", "tags": ["a"]}),
            encoding="utf-8",
        )
        item1.caption_path = "images/1.json"
        item1.mask_path = "images/1.mask.png"
        item1.has_caption = True
        item1.save()

        item2 = DatasetItem.objects.get(dataset=ds, image_path="images/2.jpg")
        cap2 = Path(root, "images/2.json")
        cap2.write_text(json.dumps({"caption": "c2"}), encoding="utf-8")
        item2.caption_path = "images/2.json"
        item2.has_caption = True
        item2.save()

        resp = self.client.get(f"/api/datasets/{ds.id}/export")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        m1 = next(d for d in data if d["filename"] == "images/1.jpg")
        self.assertEqual(m1["caption"], "c1")
        self.assertEqual(m1["title"], "t1")
        self.assertEqual(m1["tags"], ["a"])
        self.assertEqual(m1["mask"], "images/1.mask.png")

        # Import into new dataset
        ds2, root2 = self._create_dataset_with_items()
        resp2 = self.client.post(
            f"/api/datasets/{ds2.id}/import",
            data,
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)
        item = DatasetItem.objects.get(dataset=ds2, image_path="images/1.jpg")
        self.assertEqual(item.caption_path, "images/1.json")
        self.assertEqual(item.mask_path, "images/1.mask.png")
        caption_file = Path(root2, "images/1.json")
        self.assertTrue(caption_file.is_file())
        content = json.loads(caption_file.read_text(encoding="utf-8"))
        self.assertEqual(content["caption"], "c1")
        self.assertEqual(content["title"], "t1")