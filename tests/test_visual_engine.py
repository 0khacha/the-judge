import os
import shutil
import tempfile
import pytest
from the_judge.core.visual_engine import VisualEngine


def test_visual_engine_detection():
    temp_dir = tempfile.mkdtemp()
    try:
        # Non-visual directory
        ve1 = VisualEngine(temp_dir)
        is_vis, target = ve1.is_visual_workspace()
        assert is_vis is False
        assert target == ""

        # Visual directory with index.html
        html_file = os.path.join(temp_dir, "index.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write("<html><body><h1>Test App</h1></body></html>")

        ve2 = VisualEngine(temp_dir)
        is_vis2, target2 = ve2.is_visual_workspace()
        assert is_vis2 is True
        assert target2 == html_file
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_visual_screenshot_and_evaluation():
    temp_dir = tempfile.mkdtemp()
    try:
        html_file = os.path.join(temp_dir, "index.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>App</title></head><body><h1>Hello</h1></body></html>")

        ve = VisualEngine(temp_dir)
        output_dir = os.path.join(temp_dir, "_judge_visual")
        shot_path = ve.capture_screenshot(html_file, round_num=1, output_dir=output_dir)

        assert shot_path is not None
        assert os.path.exists(shot_path)

        eval_res = ve.evaluate_visual_aspects(html_file, shot_path, None)
        assert eval_res["is_visual"] is True
        assert eval_res["score"] >= 50.0
        assert "weaknesses" in eval_res
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
